# -*- coding: utf-8 -*-

"""Main module."""

# package(s) related to time, space and id
import json
import logging
import uuid

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy

# spatial libraries
import pyproj
import shapely.geometry

# additional packages
import math
import datetime, time
import copy
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SimpyObject:
    """General object which can be extended by any class requiring a simpy environment

    env: a simpy Environment
    """
    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env


class Identifiable:
    """Something that has a name and id

    name: a name
    id: a unique id generated with uuid"""

    def __init__(self, name, id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        # generate some id, in this case based on m
        self.id = id if id else str(uuid.uuid1())


class Locatable:
    """Something with a geometry (geojson format)

    geometry: can be a point as well as a polygon"""

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry


class HasContainer(SimpyObject):
    """Container class

    capacity: amount the container can hold
    level: amount the container holds initially
    container: a simpy object that can hold stuff"""

    def __init__(self, capacity, level=0, total_requested=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.container = simpy.Container(self.env, capacity, init=level)
        self.total_requested = total_requested


class EnergyUse(SimpyObject):
    """EnergyUse class
    
    energy_use_sailing:   function that specifies the fuel use during sailing activity   - input should be time
    energy_use_loading:   function that specifies the fuel use during loading activity   - input should be time
    energy_use_unloading: function that specifies the fuel use during unloading activity - input should be time

    At the moment "keeping track of fuel" is not added to the digital twin. 

    Example function could be as follows.
    The energy use of the loading event is equal to: duration * power_use.

    def energy_use_loading(power_use):
        return lambda x: x * power_use
    """

    def __init__(self, energy_use_sailing, energy_use_loading, energy_use_unloading, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.energy_use_sailing = energy_use_sailing
        self.energy_use_loading = energy_use_loading
        self.energy_use_unloading = energy_use_unloading


class HasPlume(SimpyObject):
    """Using values from Becker [2014], https://www.sciencedirect.com/science/article/pii/S0301479714005143.

    The values are slightly modified, there is no differences in dragead / bucket drip / cutterhead within this class
    sigma_d = source term fraction due to dredging
    sigma_o = source term fraction due to overflow
    sigma_p = source term fraction due to placement
    f_sett  = fraction of fines that settle within the hopper
    f_trap  = fraction of fines that are trapped within the hopper
    """

    def __init__(self, sigma_d=0.015, sigma_o=0.1, sigma_p=0.05, f_sett=0.5, f_trap=0.01, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.sigma_d = sigma_d
        self.sigma_o = sigma_o
        self.sigma_p = sigma_p
        self.f_sett = f_sett
        self.f_trap = f_trap

        self.m_r = 0


class HasSpillCondition(SimpyObject):
    """Condition to stop dredging if certain spill limits are exceeded

    limit = limit of kilograms spilled material
    start = start of the condition
    end   = end of the condition 
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        limits = []
        starts = []
        ends = []

        if type(conditions) == list:
            for condition in conditions:
                limits.append(simpy.Container(self.env, capacity = condition.spill_limit))
                starts.append(time.mktime(condition.start.timetuple()))
                ends.append(time.mktime(condition.end.timetuple()))

        else:
            limits.append(simpy.Container(self.env, capacity = conditions.spill_limit))
            starts.append(time.mktime(conditions.start.timetuple()))
            ends.append(time.mktime(conditions.end.timetuple()))
            
        self.SpillConditions = pd.DataFrame.from_dict({"Spill limit": limits,
                                                       "Criterion start": starts,
                                                       "Criterion end": ends})
    
    def check_conditions(self, spill):
        tolerance = math.inf
        waiting = 0

        for i in self.SpillConditions.index:

            if self.SpillConditions["Criterion start"][i] <= self.env.now and self.env.now <= self.SpillConditions["Criterion end"][i]:
                tolerance = self.SpillConditions["Spill limit"][i].capacity - self.SpillConditions["Spill limit"][i].level
                
                if tolerance < spill:
                    waiting = self.SpillConditions["Criterion end"][i]

                while i + 1 != len(self.SpillConditions.index) and tolerance < spill:                    
                    if self.SpillConditions["Criterion end"][i] == self.SpillConditions["Criterion start"][i + 1]:
                        tolerance = self.SpillConditions["Spill limit"][i + 1].capacity - self.SpillConditions["Spill limit"][i + 1].level
                        waiting = self.SpillConditions["Criterion end"][i + 1]
                    
                    i += 1

        return waiting


class SpillCondition():
    """Condition to stop dredging if certain spill limits are exceeded

    limit = limit of kilograms spilled material
    start = start of the condition
    end   = end of the condition 
    """

    def __init__(self, spill_limit, start, end, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.spill_limit = spill_limit
        self.start = start
        self.end = end


class HasSpill(SimpyObject):
    """Using relations from Becker [2014], https://www.sciencedirect.com/science/article/pii/S0301479714005143."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
    
    def spillDredging(self, processor, mover, density, fines, volume, dredging_duration, overflow_duration = 0):
        """Calculate the spill due to the dredging activity
        
        density = the density of the dredged material
        fines   = the percentage of fines in the dredged material
        volume  = the dredged volume
        dredging_duration = duration of the dredging event
        overflow_duration = duration of the dredging event whilst overflowing
        
        m_t = total mass of dredged fines per cycle
        m_d = total mass of spilled fines during one dredging event
        m_h = total mass of dredged fines that enter the hopper
        
        m_o  = total mass of fine material that leaves the hopper during overflow
        m_op = total mass of fines that are released during overflow that end in dredging plume
        m_r  = total mass of fines that remain within the hopper"""

        m_t = density * fines * volume
        m_d = processor.sigma_d * m_t
        m_h = m_t - m_d
        
        m_o = (overflow_duration / dredging_duration) * (1 - mover.f_sett) * (1 - mover.f_trap) * m_h
        m_op = mover.sigma_o * m_o
        mover.m_r = m_h - m_o

        if isinstance(self, Log):
            self.log_entry("fines released", self.env.now, m_d + m_op, self.geometry)

        return m_d + m_op

    def spillPlacement(self, processor, mover):
        """Calculate the spill due to the placement activity"""
        if isinstance(self, Log):
            self.log_entry("fines released", self.env.now, mover.m_r * processor.sigma_p, self.geometry)

        return mover.m_r * processor.sigma_p


class SoilLayer:
    """ Create a soillayer

    layer = layer number, 0 to n, with 0 the layer at the surface
    material = name of the dredged material
    density = density of the dredged material
    fines = fraction of total that is fine material
    """

    def __init__(self, layer, volume, material, density, fines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.layer = layer
        self.volume = volume
        self.material = material
        self.density = density
        self.fines = fines


class HasSoil:
    """ Add soil properties to an object

    soil = list of SoilLayer objects
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.soil = {}
    
    def add_layer(self, soillayer):
        """Add a layer based on a SoilLayer object."""
        for key in self.soil:
            if key == "Layer {:04d}".format(soillayer.layer):
                print("Soil layer named **Layer {:04d}** already exists".format(soillayer.layer))

        # Add soillayer to self
        self.soil["Layer {:04d}".format(soillayer.layer)] = {"Layer": soillayer.layer,
                                                              "Volume": soillayer.volume,
                                                              "Material": soillayer.material,
                                                              "Density": soillayer.density,
                                                              "Fines": soillayer.fines}

        # Make sure that self.soil is always a sorted dict based on layernumber
        soil = copy.deepcopy(self.soil)
        self.soil = {}

        for key in sorted(soil):
            self.soil[key] = soil[key]
    
    def add_layers(self, soillayers):
        """Add a list layers based on a SoilLayer object."""
        for layer in soillayers:
            self.add_layer(layer)
    
    def total_volume(self):
        """Determine the total volume of soil."""
        total_volume = 0

        for layer in self.soil:
            total_volume += self.soil[layer]["Volume"]
        
        return total_volume
    
    def weighted_average(self, layers, volumes):
        """Create a new SoilLayer object based on the weighted average parameters of extracted layers.
        
        len(layers) should be len(volumes)"""
        densities = []
        fines = []
        name = "Mixture of: "
    
        for i, layer in enumerate(layers):
            if 0 < volumes[i]:
                densities.append(self.soil[layer]["Density"])
                fines.append(self.soil[layer]["Fines"])
                name += (self.soil[layer]["Material"] + ", ")
            else:
                densities.append(0)
                fines.append(0)

        return SoilLayer(0, sum(volumes), name.rstrip(", "), np.average(np.asarray(densities), weights = np.asarray(volumes)), 
                                                             np.average(np.asarray(fines), weights = np.asarray(volumes)))
    
    def get_soil(self, volume):
        """Remove soil from self."""

        # If soil is a mover, the mover should be initialized with an empty soil dict after emptying
        if isinstance(self, Movable) and volume == self.container.level:
            removed_soil = list(self.soil.items())[0]

            self.soil = {}

            return SoilLayer(0,
                             removed_soil[1]["Volume"],
                             removed_soil[1]["Material"],
                             removed_soil[1]["Density"],
                             removed_soil[1]["Fines"])

        # In all other cases the soil dict should remain, with updated values
        else:
            removed_volume = 0
            layers = []
            volumes = []
            
            for layer in sorted(self.soil):
                if (volume - removed_volume) <= self.soil[layer]["Volume"]:
                    layers.append(layer)
                    volumes.append(volume - removed_volume)
                    
                    self.soil[layer]["Volume"] -= (volume - removed_volume)
                    
                    break
                
                else:
                    removed_volume += self.soil[layer]["Volume"]
                    layers.append(layer)
                    volumes.append(self.soil[layer]["Volume"])

                    self.soil[layer]["Volume"] = 0

            return self.weighted_average(layers, volumes)
    
    def put_soil(self, soillayer):
        """Add soil to self.
        
        Add a layer based on a SoilLayer object."""
        # If already soil available
        if self.soil:
            # Can be moveable --> mix
            if isinstance(self, Movable):
                pass

            # Can be site --> add layer or add volume
            else:
                top_layer = list(sorted(self.soil.keys()))[0]
            
                # If toplayer material is similar to added material --> add volume
                if (self.soil[top_layer]["Material"] == soillayer.material and \
                    self.soil[top_layer]["Density"] == soillayer.density and \
                    self.soil[top_layer]["Fines"] == soillayer.fines):

                    self.soil[top_layer]["Volume"] += soillayer.volume
                
                # If not --> add layer
                else:
                    layers = copy.deepcopy(self.soil)
                    self.soil = {}
                    self.add_layer(soillayer)

                    for key in sorted(layers):
                        layers[key]["Layer"] += 1
                        self.add_layer(SoilLayer(layers[key]["Layer"], 
                                                 layers[key]["Volume"], 
                                                 layers[key]["Material"], 
                                                 layers[key]["Density"], 
                                                 layers[key]["Fines"]))

        # If no soil yet available, add layer
        else:
            self.add_layer(soillayer)
    
    def get_properties(self, amount):
        """Get the soil properties for a certain amount"""
        volumes = []
        layers = []
        volume = 0

        for layer in sorted(self.soil):
            if (amount - volume) <= self.soil[layer]["Volume"]:
                volumes.append(amount - volume)
                layers.append(layer)
                break
            else:
                volumes.append(self.soil[layer]["Volume"])
                layers.append(layer)
                volume += self.soil[layer]["Volume"]

        properties = self.weighted_average(layers, volumes)

        return properties.density, properties.fines

class Movable(SimpyObject, Locatable):
    """Movable class

    Used for object that can move with a fixed speed
    geometry: point used to track its current location
    v: speed"""

    def __init__(self, v=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v = v
        self.wgs84 = pyproj.Geod(ellps='WGS84')

    def move(self, destination):
        """determine distance between origin and destination, and
        yield the time it takes to travel it"""
        # Determine distance based on geometry objects
        distance = self.get_distance(self.geometry, destination)

        # Determine speed based on filling degree
        speed = self.current_speed

        # Check out the time based on duration of sailing event
        yield self.env.timeout(distance / speed)
        
        # Set mover geometry to destination geometry
        self.geometry = shapely.geometry.asShape(destination.geometry)

        # Compute the energy use
        if isinstance(self, EnergyUse):
            energy = self.energy_use_sailing(distance / speed)
            message = "Energy use " + self.log["Message"][-1].rstrip(" start")
            self.log_entry(message, self.env.now, energy, self.geometry)
        
        # Debug logs
        logger.debug('  distance: ' + '%4.2f' % distance + ' m')
        logger.debug('  sailing:  ' + '%4.2f' % speed + ' m/s')
        logger.debug('  duration: ' + '%4.2f' % ((distance / speed) / 3600) + ' hrs')


    def is_at(self, locatable, tolerance=100):
        current_location = shapely.geometry.asShape(self.geometry)
        other_location = shapely.geometry.asShape(locatable.geometry)
        _, _, distance = self.wgs84.inv(current_location.x, current_location.y,
                                        other_location.x, other_location.y)
        
        return distance < tolerance

    def get_distance(self, origin, destination):
        orig = shapely.geometry.asShape(self.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        return distance

    @property
    def current_speed(self):
        return self.v


class ContainerDependentMovable(Movable, HasContainer):
    """ContainerDependentMovable class

    Used for objects that move with a speed dependent on the container level
    compute_v: a function, given the fraction the container is filled (in [0,1]), returns the current speed"""

    def __init__(self,
                 compute_v,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_v = compute_v
        self.wgs84 = pyproj.Geod(ellps='WGS84')

    @property
    def current_speed(self):
        return self.compute_v(self.container.level / self.container.capacity)


class HasResource(SimpyObject):
    """HasProcessingLimit class

    Adds a limited Simpy resource which should be requested before the object is used for processing."""

    def __init__(self, nr_resources=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=nr_resources)


class Log(SimpyObject):
    """Log class

    log: log message [format: 'start activity' or 'stop activity']
    t: timestamp
    value: a value can be logged as well
    geometry: value from locatable (lat, lon)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.log = {"Message": [],
                    "Timestamp": [],
                    "Value": [],
                    "Geometry": []}

    def log_entry(self, log, t, value, geometry_log):
        """Log"""
        self.log["Message"].append(log)
        self.log["Timestamp"].append(t)
        self.log["Value"].append(value)
        self.log["Geometry"].append(geometry_log)

    def get_log_as_json(self):
        json = []
        for msg, t, value, geometry_log in zip(self.log["Message"], self.log["Timestamp"], self.log["Value"], self.log["Geometry"]):
            json.append(dict(message=msg, time=t, value=value, geometry_log=geometry_log))
        return json


class Processor(SimpyObject):
    """Processor class

    loading_func:   lambda function to determine the duration of loading event based on input parameter amount 
    unloading_func: lambda function to determine the duration of unloading event based on input parameter amount 
    
    Example function could be as follows.
    The duration of the loading event is equal to: amount / rate.

    def loading_func(loading_rate):
        return lambda x: x / loading_rate

    
    A more complex example function could be as follows.
    The duration of the loading event is equal to: manoeuvring + amount / rate + cleaning.

    def loading_func(manoeuvring, loading_rate, cleaning):
        return lambda x: datetime.timedelta(minutes = manoeuvring).total_seconds() + \
                         x / loading_rate + \
                         datetime.timedelta(minutes = cleaning).total_seconds()

    """

    def __init__(self, loading_func = None, unloading_func = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.loading_func = loading_func
        self.unloading_func = unloading_func

    # noinspection PyUnresolvedReferences
    def process(self, origin, destination, amount, origin_resource_request=None, destination_resource_request=None):
        """get amount from origin container, put amount in destination container,
        and yield the time it takes to process it"""

        # Make sure all requests are granted
        assert isinstance(origin, HasContainer) and isinstance(destination, HasContainer)
        assert isinstance(origin, HasResource) and isinstance(destination, HasResource)
        assert isinstance(origin, Log) and isinstance(destination, Log)

        assert origin.container.level >= amount
        assert destination.container.capacity - destination.container.level >= amount

        my_origin_turn = origin_resource_request
        if my_origin_turn is None:
            my_origin_turn = origin.resource.request()

        my_dest_turn = destination_resource_request
        if my_dest_turn is None:
            my_dest_turn = destination.resource.request()

        yield my_origin_turn
        yield my_dest_turn

        # If requests are yielded, start activity
        # Waiting event should be combined to check if all conditions allow starting
        # Activity can only start if environmental conditions allow it
        yield from self.checkSpill(origin, destination, amount)

        # If environmental conditions allow starting the activity, check if there is a weather window
        # yield from self.checkWeather / self.checkTide

        # Log the start of the activity     
        origin.log_entry('unloading start', self.env.now, origin.container.level, self.geometry)
        destination.log_entry('loading start', self.env.now, destination.container.level, self.geometry)

        # Add spill the location where processing is taking place
        self.addSpill(origin, destination, amount, self.rate(amount))

        # Shift soil from container volumes
        self.shiftSoil(origin, destination, amount)

        # Shift volumes in containers
        origin.container.get(amount)
        destination.container.put(amount)

        # Checkout the time
        yield self.env.timeout(self.rate(amount))

        # Compute the energy use
        self.computeEnergy(self.rate(amount), origin, destination)

        # Log the end of the activity
        origin.log_entry('unloading stop', self.env.now, origin.container.level, self.geometry)
        destination.log_entry('loading stop', self.env.now, destination.container.level, self.geometry)

        logger.debug('  process:        ' + '%4.2f' % ((self.rate(amount)) / 3600) + ' hrs')

        if origin_resource_request is None:
            origin.resource.release(my_origin_turn)
        if destination_resource_request is None:
            destination.resource.release(my_dest_turn)
    
    
    def computeEnergy(self, duration, origin, destination):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could consume energy
          2. Processor is also destination, origin could consume energy
          3. Processor is neither destination, nor origin, but both could consume energy
        """

        # If self == origin --> unloading
        if self == origin:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_unloading(duration)
                message = "Energy use unloading"
                self.log_entry(message, self.env.now, energy, self.geometry)
            if isinstance(destination, EnergyUse):
                energy = destination.energy_use_loading(duration)
                message = "Energy use loading"
                destination.log_entry(message, self.env.now, energy, destination.geometry)

        # If self == destination --> loading
        elif self == destination:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_unloading(duration)
                message = "Energy use loading"
                self.log_entry(message, self.env.now, energy, self.geometry)
            if isinstance(origin, EnergyUse):
                energy = origin.energy_use_loading(duration)
                message = "Energy use unloading"
                origin.log_entry(message, self.env.now, energy, origin.geometry)

        # If self != origin and self != destination --> processing
        else:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_loading(duration)
                message = "Energy use loading"
                self.log_entry(message, self.env.now, energy, self.geometry)
            if isinstance(origin, EnergyUse):
                energy = origin.energy_use_unloading(duration)
                message = "Energy use unloading"
                origin.log_entry(message, self.env.now, energy, origin.geometry)
            if isinstance(destination, EnergyUse):
                energy = destination.energy_use_loading(duration)
                message = "Energy use loading"
                destination.log_entry(message, self.env.now, energy, destination.geometry)

    
    def checkSpill(self, origin, destination, amount):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could have spill requirements
          2. Processor is also destination, origin could have spill requirements
          3. Processor is neither destination, nor origin, but both could have spill requirements

        Result of this function is possible waiting, spill is added later on and does not depend on possible requirements
        """

        # If self == origin --> destination is a placement location
        if self == origin:
            if isinstance(destination, HasSpillCondition) and isinstance(self, HasSoil) and isinstance(self, HasPlume):
                density, fines = self.get_properties(amount)
                spill = self.sigma_d * density * fines * amount

                waiting = destination.check_conditions(spill)
                
                if 0 < waiting:
                    self.log_entry('waiting for spill start', self.env.now, 0, self.geometry)
                    yield self.env.timeout(waiting - self.env.now)
                    self.log_entry('waiting for spill stop', self.env.now, 0, self.geometry)

        # If self == destination --> origin is a retrieval location
        elif self == destination:
            if isinstance(origin, HasSpillCondition) and isinstance(origin, HasSoil) and isinstance(self, HasPlume):
                density, fines = origin.get_properties(amount)
                spill = self.sigma_d * density * fines * amount

                waiting = origin.check_conditions(spill)
                
                if 0 < waiting:
                    self.log_entry('waiting for spill start', self.env.now, 0, self.geometry)
                    yield self.env.timeout(waiting - self.env.now)
                    self.log_entry('waiting for spill stop', self.env.now, 0, self.geometry)


        # If self != origin and self != destination --> processing
        else:
            if isinstance(destination, HasSpillCondition) and isinstance(origin, HasSoil) and isinstance(self, HasPlume):
                density, fines = origin.get_properties(amount)
                spill = self.sigma_d * density * fines * amount

                waiting = destination.check_conditions(spill)
                
                if 0 < waiting:
                    self.log_entry('waiting for spill start', self.env.now, 0, self.geometry)
                    yield self.env.timeout(waiting - self.env.now)
                    self.log_entry('waiting for spill stop', self.env.now, 0, self.geometry)


    def addSpill(self, origin, destination, amount, duration):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could have spill requirements
          2. Processor is also destination, origin could have spill requirements
          3. Processor is neither destination, nor origin, but both could have spill requirements

        Result of this function is possible waiting, spill is added later on and does not depend on possible requirements
        """

        if isinstance(origin, HasSoil):
            density, fines = origin.get_properties(amount)

            # If self == origin --> destination is a placement location
            if self == origin:
                if isinstance(destination, HasSpillCondition) and isinstance(self, HasPlume):
                    spill = destination.spillPlacement(self, self)
                
                    if spill > 0 and isinstance(destination, HasSpillCondition):
                        for condition in destination.SpillConditions["Spill limit"]:
                            condition.put(spill)

            # If self == destination --> origin is a retrieval location
            elif self == destination:
                if isinstance(origin, HasSpillCondition) and isinstance(self, HasPlume):
                    spill = origin.spillDredging(self, self, density, fines, amount, duration)
                
                    if spill > 0 and isinstance(destination, HasSpillCondition):
                        for condition in destination.SpillConditions["Spill limit"]:
                            condition.put(spill)

            # If self != origin and self != destination --> processing
            else:
                if isinstance(destination, HasSpillCondition) and isinstance(self, HasPlume):
                    spill = destination.spillPlacement(self, origin)
                
                    if spill > 0 and isinstance(destination, HasSpillCondition):
                        for condition in destination.SpillConditions["Spill limit"]:
                            condition.put(spill)
    

    def shiftSoil(self, origin, destination, amount):
        """
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)
        amount: the volume of soil that is moved

        Can only occur if both the origin and the destination have soil objects (mix-ins)
        """
        
        if isinstance(origin, HasSoil) and isinstance(destination, HasSoil):
            soil = origin.get_soil(amount)
            destination.put_soil(soil)


class DictEncoder(json.JSONEncoder):
    """serialize a simpy digital_twin object to json"""
    def default(self, o):
        result = {}
        for key, val in o.__dict__.items():
            if isinstance(val, simpy.Environment):
                continue
            if isinstance(val, simpy.Container):
                result['capacity'] = val.capacity
                result['level'] = val.level
            elif isinstance(val, simpy.Resource):
                result['nr_resources'] = val.capacity
            else:
                result[key] = val

        return result


def serialize(obj):
    return json.dumps(obj, cls=DictEncoder)
