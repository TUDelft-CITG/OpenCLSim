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


class HasFuel(SimpyObject):
    """HasFuel class

    fuel_use_loading: function that specifies the fuel use during loading activity
    fuel_use_unloading: function that specifies the fuel use during unloading activity
    fuel_use_sailing: function that specifies the fuel use during sailing activity

    fuel_capacity: amount of fuel that the container can hold
    fuel_level: amount the container holds initially
    fuel_container: a simpy object that can hold stuff
    refuel_method: method of refueling (bunker or returning to quay) or ignore for not tracking
    """

    def __init__(self, fuel_use_loading, fuel_use_unloading, fuel_use_sailing, 
                 fuel_capacity, fuel_level, refuel_method="ignore", *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.fuel_use_loading = fuel_use_loading
        self.fuel_use_unloading = fuel_use_unloading
        self.fuel_use_sailing = fuel_use_sailing
        self.fuel_container = simpy.Container(self.env, fuel_capacity, init=fuel_level)
        self.refuel_method = refuel_method

    def consume(self, amount):
        """consume an amount of fuel"""
        
        self.log_entry("fuel consumed", self.env.now, amount, self.geometry)
        self.fuel_container.get(amount)

    def fill(self, fuel_delivery_rate=1):
        """fill 'er up"""

        amount = self.fuel_container.capacity - self.fuel_container.level
        if 0 < amount:
            self.fuel_container.put(amount)

        if self.refuel_method == "ignore":
            return 0
        else:
            return amount / fuel_delivery_rate
    
    def check_fuel(self, fuel_use):
        if self.fuel_container.level < fuel_use:
            #latest_log = [self.log[-1], self.t[-1], self.value[-1]]
            #del self.log[-1], self.t[-1], self.value[-1]

            refuel_duration = self.fill()

            if refuel_duration != 0:
                self.log_entry("fuel loading start", self.env.now, self.fuel_container.level, self.geometry)
                yield self.env.timeout(refuel_duration)
                self.log_entry("fuel loading stop", self.env.now, self.fuel_container.level, self.geometry)

            #self.log_entry(latest_log[0], self.env.now, latest_log[2])


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


class HasWeather:
    """HasWeather class

    Used to add weather conditions to a project site
    name: name of .csv file in folder

    year: name of the year column
    month: name of the month column
    day: name of the day column

    timestep: size of timestep to interpolate between datapoints (minutes)
    bed: level of the seabed / riverbed with respect to CD (meters)
    """

    def __init__(self, file, year, month, day, hour, timestep=10, bed=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        df = pd.read_csv(file)
        df.index = df[[year, month, day, hour]].apply(lambda s : datetime.datetime(*s), axis = 1)
        df = df.drop([year, month, day, hour],axis=1)
        
        self.timestep = datetime.timedelta(minutes = timestep)

        data = {}
        for key in df:
            series = (pd.Series(df[key], index = df.index)
                      .fillna(0)
                      .resample(self.timestep)
                      .interpolate("linear"))
            
            data[key] = series.values

        data["Index"] = series.index
        self.metocean_data = pd.DataFrame.from_dict(data)
        self.metocean_data.index = self.metocean_data["Index"]
        self.metocean_data.drop(["Index"], axis = 1, inplace = True)

        if bed:
            self.metocean_data["Water depth"] = self.metocean_data["Tide"] - bed


class HasWorkabilityCriteria:
    """HasWorkabilityCriteria class

    Used to add workability criteria
    """

    def __init__(self, v=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v = v
        self.wgs84 = pyproj.Geod(ellps='WGS84')


class WorkabilityCriterion:
    """WorkabilityCriterion class

    Used to add limits to vessels (and therefore acitivities)
    condition: column name of the metocean data (Hs, Tp, etc.)
    maximum: maximum value 
    minimum: minimum value
    window_length: minimal length of the window (minutes)"""

    def __init__(self, prop, max, min, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.wgs84 = pyproj.Geod(ellps='WGS84')


class HasDepthRestriction:
    """HasDepthRestriction class

    Used to add depth limits to vessels
    draught: should be a lambda function with input variable container.volume
    waves: list with wave_heights
    ukc: list with ukc, corresponding to wave_heights
    """

    def __init__(self, compute_draught, waves, ukc, filling=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_draught = compute_draught
        self.waves = waves
        self.ukc = ukc
        self.filling = filling

        self.depth_data = {}
    
    def check_depth_restriction(self, location):
        fill_degree = self.container.level / self.container.capacity
        time = datetime.datetime.utcfromtimestamp(self.env.now)
        waiting = 0

        for key in sorted(self.depth_data[location.name].keys()):
            if fill_degree <= key:
                series = self.depth_data[location.name][key]["Series"]
                
                if len(series) == 0:
                    print("No actual allowable draught available - starting anyway.")
                    waiting = 0
                
                else:
                    a = series.values
                    v = np.datetime64(time - location.timestep)

                    index = np.searchsorted(a, v, side='right')
                    
                    try:
                        next_window = series[index] - time
                    except IndexError:
                        print("Length weather data exceeded - continuing without weather.")
                        next_window = series[-1] - time

                    waiting = max(next_window, datetime.timedelta(0)).total_seconds()

                break
        
        if waiting != 0:
            self.log_entry('waiting for tide start', self.env.now, waiting, self.geometry)
            yield self.env.timeout(waiting)
            self.log_entry('waiting for tide stop', self.env.now, waiting, self.geometry)

    def calc_depth_restrictions(self, location):
        # Minimal waterdepth should be draught + ukc
        # Waterdepth is tide - depth site
        # For full to empty [0%, 20%, 40%, 60%, 80%, 100%]

        self.depth_data[location.name] = {}

        for i in np.linspace(0.20, 1, 9):
            df = location.metocean_data.copy()
            
            draught = self.compute_draught(i)
            df["Required depth"] = df["Hs"].apply(lambda s : self.calc_required_depth(draught, s))
            series = pd.Series(df["Required depth"] < df["Water depth"])

            # Make a series on which the activity can start
            duration = i * self.container.capacity / self.rate
            steps = max(int(duration / location.timestep.seconds + .5), 1)
            windowed = series.rolling(steps)
            windowed = windowed.max().shift(-steps + 1)
            windowed = windowed[windowed.values == 1].index

            self.depth_data[location.name][i] = {"Volume": i * self.container.capacity,
                                                 "Draught": draught,
                                                 "Series": windowed}
    
    def calc_required_depth(self, draught, wave_height):
        required_depth = np.nan

        for i, wave in enumerate(self.waves):
            if wave_height <= wave:
                required_depth = self.ukc[i] + draught
        
        return required_depth

    @property
    def current_draught(self):
        return self.compute_draught(self.container.level / self.container.capacity)


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
        orig = shapely.geometry.asShape(self.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        forward, backward, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        speed = self.current_speed

        # check for sufficient fuel
        if isinstance(self, HasFuel):
            fuel_consumed = self.fuel_use_sailing(distance, speed)
            self.check_fuel(fuel_consumed)

        yield self.env.timeout(distance / speed)
        self.geometry = dest
        logger.debug('  distance: ' + '%4.2f' % distance + ' m')
        logger.debug('  sailing:  ' + '%4.2f' % speed + ' m/s')
        logger.debug('  duration: ' + '%4.2f' % ((distance / speed) / 3600) + ' hrs')

        # lower the fuel
        if isinstance(self, HasFuel):
            # remove seconds of fuel
            self.consume(fuel_consumed)

    def is_at(self, locatable, tolerance=100):
        current_location = shapely.geometry.asShape(self.geometry)
        other_location = shapely.geometry.asShape(locatable.geometry)
        _, _, distance = self.wgs84.inv(current_location.x, current_location.y,
                                        other_location.x, other_location.y)
        return distance < tolerance

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
        self.log["Timestamp"].append(datetime.datetime.fromtimestamp(t))
        self.log["Value"].append(value)
        self.log["Geometry"].append(geometry_log)

    def get_log_as_json(self):
        json = []
        for msg, t, value, geometry_log in zip(self.log["Message"], self.log["Timestamp"], self.log["Value"], self.log["Geometry"]):
            json.append(dict(message=msg, time=t, value=value, geometry_log=geometry_log))
        return json


class Processor(SimpyObject):
    """Processor class

    rate: rate with which quantity can be processed [amount/s]"""

    def __init__(self, rate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.rate = rate

    # noinspection PyUnresolvedReferences
    def process(self, origin, destination, amount, origin_resource_request=None, destination_resource_request=None):
        """get amount from origin container, put amount in destination container,
        and yield the time it takes to process it"""
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

        #######################################
        ############### ON FUEL USE
        ############### THIS SHOULD BE IMPROVED

        # check fuel from origin
        if isinstance(origin, HasFuel):
            fuel_consumed_origin = origin.fuel_use_unloading(amount, self.rate)
            origin.check_fuel(fuel_consumed_origin)

        # check fuel from destination
        if isinstance(destination, HasFuel):
            fuel_consumed_destination = destination.fuel_use_unloading(amount, self.rate)
            destination.check_fuel(fuel_consumed_destination)
        
        # check fuel from processor if not origin or destination  -- case if processor != mover
        if self.id != origin.id and self.id != destination.id and isinstance(self, HasFuel):
            # if origin is moveable -- e.g. unloading a barge with a crane
            if isinstance(origin, Movable):
                fuel_consumed = self.fuel_use_unloading(amount, self.rate)
                self.check_fuel(fuel_consumed)
            
            # if destination is moveable -- e.g. loading a barge with a backhoe
            if isinstance(destination, Movable):
                fuel_consumed = self.fuel_use_loading(amount, self.rate)
                self.check_fuel(fuel_consumed)

            # third option -- from moveable to moveable -- take highest fuel consumption
            else:
                fuel_consumed = max(self.fuel_use_unloading(amount, self.rate), self.fuel_use_loading(amount, self.rate))
                self.check_fuel(fuel_consumed)
        
        ############### THIS SHOULD BE IMPROVED
        ############### ON Fuel
        #######################################


        #######################################
        ############### ON Spill
        #######################################
        yield from self.checkSpill(origin, destination, amount)

        #######################################
        ############### ON Weather
        #######################################
        if isinstance(origin, HasDepthRestriction) and isinstance(origin, Movable) and isinstance(destination, HasWeather):
            yield from origin.check_depth_restriction(destination)
        elif isinstance(destination, HasDepthRestriction) and isinstance(destination, Movable) and isinstance(origin, HasWeather):
            yield from destination.check_depth_restriction(origin)
                
        origin.log_entry('unloading start', self.env.now, origin.container.level, self.geometry)
        destination.log_entry('loading start', self.env.now, destination.container.level, self.geometry)

        # Move soil from origin to destination
        if isinstance(origin, HasSoil) and isinstance(destination, HasSoil):
            soil = origin.get_soil(amount)
            destination.put_soil(soil)

            self.addSpill(soil, origin, destination, amount, amount / self.rate)

        origin.container.get(amount)
        destination.container.put(amount)

        if self.id == origin.id:
            yield self.env.timeout(amount / self.rate + datetime.timedelta(minutes = 20).total_seconds())
        else:
            yield self.env.timeout(amount / self.rate)

        # lower the fuel for all active entities
        if isinstance(origin, HasFuel):
            origin.consume(fuel_consumed_origin)

        if isinstance(destination, HasFuel):
            destination.consume(fuel_consumed_destination)

        if self.id != origin.id and self.id != destination.id and isinstance(self, HasFuel):
            self.consume(fuel_consumed)

        origin.log_entry('unloading stop', self.env.now, origin.container.level, self.geometry)
        destination.log_entry('loading stop', self.env.now, destination.container.level, self.geometry)

        logger.debug('  process:        ' + '%4.2f' % ((amount / self.rate) / 3600) + ' hrs')

        if origin_resource_request is None:
            origin.resource.release(my_origin_turn)
        if destination_resource_request is None:
            destination.resource.release(my_dest_turn)
    
    def checkFuel(self):
        pass
    
    def checkSpill(self, origin, destination, amount):
        # Before processing can start, check the conditions
        if self.id != origin.id and isinstance(origin, HasSpillCondition) and isinstance(origin, HasSoil) and isinstance(self, HasPlume):
            # In this case "destination" is the "mover"
            density, fines = origin.get_properties(amount)
            spill = self.sigma_d * density * fines * amount

            waiting = origin.check_conditions(spill)
            
            if 0 < waiting:
                self.log_entry('waiting for spill start', self.env.now, 0, destination.geometry)
                yield self.env.timeout(waiting - self.env.now)
                self.log_entry('waiting for spill stop', self.env.now, 0, destination.geometry)

        elif self.id != destination.id and isinstance(destination, HasSpillCondition) and isinstance(origin, HasSoil) and isinstance(self, HasPlume):
            # In this case "origin" is the "mover"
            spill = origin.m_r * self.sigma_p
            waiting = destination.check_conditions(spill)
            
            if 0 < waiting:
                self.log_entry('waiting for spill start', self.env.now, 0, origin.geometry)
                yield self.env.timeout(waiting - self.env.now)
                self.log_entry('waiting for spill stop', self.env.now, 0, origin.geometry)
    
    def addSpill(self, soil, origin, destination, amount, duration):
        density, fines = soil.density, soil.fines
            
        if self.id == destination.id and isinstance(origin, HasSpillCondition):
            # In this case "destination" is the "mover"
            spill = origin.spillDredging(self, destination, density, fines, amount, duration)
        
            if spill > 0 and isinstance(origin, HasSpillCondition):
                for condition in origin.SpillConditions["Spill limit"]:
                    condition.put(spill)

        elif self.id == origin.id and isinstance(destination, HasSpillCondition):
            # In this case "origin" is the "mover"
            spill = destination.spillPlacement(self, origin)
        
            if spill > 0 and isinstance(destination, HasSpillCondition):
                for condition in destination.SpillConditions["Spill limit"]:
                    condition.put(spill)


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
