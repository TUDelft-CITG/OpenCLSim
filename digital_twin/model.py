import digital_twin.core as core
import datetime
import shapely
import shapely.geometry
import scipy.interpolate
import scipy.integrate
import pandas as pd
import numpy as np


class LevelCondition:
    """The LevelCondition class can be used to specify the start level and stop level conditions for an Activity.

    container: an object which extends HasContainer, the container whose level needs to be >= or <= a certain value
    min_level: the minimum level the container is required to have
    max_level: the maximum level the container is required to have
    """

    def __init__(self, container, min_level=None, max_level=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.container = container
        self.min_level = min_level if min_level is not None else 0
        self.max_level = max_level if max_level is not None else container.container.capacity

    def satisfied(self):
        current_level = self.container.container.level
        return self.min_level <= current_level <= self.max_level


class TimeCondition:
    """The TimeCondition class can be used to specify the period in which an activity can take place

    environment: the environment in which the simulation takes place
    start: the start date of the condition
    end: the end date of the condition
    """

    def __init__(self, environment, start = None, stop = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.env = environment
        self.start = start if start is not None else datetime.datetime.fromtimestamp(self.env.now)
        self.stop = stop if stop is not None else datetime.datetime.fromtimestamp(self.env.now)
    
    def satisfied(self):
        current_time = datetime.datetime.fromtimestamp(self.env.now)
        return self.start <= current_time >= self.stop


class AndCondition:
    """The AndCondition class can be used to combine several different conditions into a single condition for an Activity.

    conditions: a list of condition objects that need to all be satisfied for the condition to be satisfied
                each object should have a satisfied method that returns whether the condition is satisfied or not
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.conditions = conditions

    def satisfied(self):
        for condition in self.conditions:
            if not condition.satisfied():
                return False
        return True


class OrCondition:
    """The AndCondition class can be used to combine several different conditions into a single condition for an Activity.

    conditions: a list of condition objects, one of which needs to be satisfied for the condition to be satisfied
                each object should have a satisfied method that returns whether the condition is satisfied or not
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.conditions = conditions

    def satisfied(self):
        for condition in self.conditions:
            if condition.satisfied():
                return True
        return False


class TrueCondition:
    """The TrueCondition class defines a condition which is always satisfied."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    def satisfied(self):
        return True


class Activity(core.Identifiable, core.Log):
    """The Activity Class forms a specific class for a single activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    start_condition: the activity will start as soon as this condition is satisfied
                     by default will always be True
    stop_condition: the activity will stop (terminate) as soon as this condition is no longer satisfied after
                    the activity has started
                    by default will always be for the destination container to be full or the source container to be empty
    condition: after the activity has started (start_condition was satisfied), this condition will be checked as long
               as the stop_condition is not satisfied, if the condition returns True, the activity will complete exactly
               one transportation of substances, of the condition is False the activity will wait for the condition to
               be satisfied again
               by default will always be True
    origin: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    loader: object which will get units from 'origin' Container and put them into 'mover' Container
            should inherit from Processor, HasResource, Identifiable and Log
            after the simulation is complete, its log will contain entries for each time it
            started loading and stopped loading
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    unloader: gets amount from 'mover' Container and puts it into 'destination' Container
              should inherit from Processor, HasResource, Identifiable and Log
              after the simulation is complete, its log will contain entries for each time it
              started unloading and stopped unloading
    """

    # todo should loader and unloader also inherit from Locatable and Activity include checks if the loader / unloader is at the correct location?

    def __init__(self,
                 origin, destination,
                 loader, mover, unloader,
                 start_condition=None, stop_condition=None, condition=None,
                 show=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.start_condition = start_condition if start_condition is not None else TrueCondition()
        self.stop_condition = stop_condition if stop_condition is not None else OrCondition(
            [LevelCondition(origin, max_level=0),
             LevelCondition(destination, min_level=destination.container.capacity)])
        self.condition = condition if condition is not None else TrueCondition()
        self.origin = origin
        self.destination = destination
        self.loader = loader
        self.mover = mover
        self.unloader = unloader

        self.print = show

        self.installation_proc = self.env.process(
            self.process_control(self.start_condition, self.stop_condition, self.condition,
                                 self.origin, self.destination, self.loader, self.mover, self.unloader)
        )

    def process_control(self, start_condition, stop_condition, condition,
                        origin, destination,
                        loader, mover, unloader):
        """Installation process control"""

        # wait for the start condition to be satisfied
        # checking the general condition and move

        # stand by until the start condition is satisfied
        shown = False
        while not start_condition.satisfied():
            if not shown:
                print('T=' + '{:06.2f}'.format(self.env.now) + ' ' + self.name +
                      ' to ' + destination.name + ' suspended')
                self.log_entry("suspended", self.env.now, -1, origin.geometry)
                shown = True
            yield self.env.timeout(3600)  # step 3600 time units ahead

        # todo add nice printing to the conditions, then print them here
        print('T=' + '{:06.2f}'.format(self.env.now) + ' Start condition is satisfied, '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' started')
        self.log_entry("started", self.env.now, -1, origin.geometry)

        # keep moving substances until the stop condition is satisfied
        while not stop_condition.satisfied():
            if condition.satisfied():
                yield from perform_single_run(self.env, self, origin, destination, loader, mover, unloader, verbose=self.print)
            else:
                yield self.env.timeout(3600)

        print('T=' + '{:06.2f}'.format(self.env.now) + ' Stop condition is satisfied, '
              + self.name + ' transporting from ' + origin.name + ' to ' + destination.name + ' complete')
        self.log_entry("completed", self.env.now, -1, destination.geometry)


def perform_single_run(environment, activity_log, origin, destination, loader, mover, unloader, verbose=False):
        """Installation process"""
        # estimate amount that should be transported
        amount = min(
            mover.container.capacity - mover.container.level,
            origin.container.level,
            origin.container.capacity - origin.total_requested,
            destination.container.capacity - destination.container.level,
            destination.container.capacity - destination.total_requested)
        
        if isinstance(mover, core.HasDepthRestriction): amount = min(amount, mover.check_optimal_filling(loader, unloader, origin, destination))

        if amount > 0:
            # request access to the transport_resource
            origin.total_requested += amount
            destination.total_requested += amount

            if verbose == True:
                print('Using ' + mover.name + ' to process ' + str(amount))
            activity_log.log_entry("transporting start", environment.now, amount, mover.geometry)

            with mover.resource.request() as my_mover_turn:
                yield my_mover_turn

                # move to the origin if necessary
                if not mover.is_at(origin):
                    yield from move_mover(environment, mover, origin, 'empty', verbose=verbose)

                # load the mover
                loader.rate = loader.loading_func        # rate is variable to loading / unloading
                yield from shift_amount(environment, amount, loader, origin, mover, destination_resource_request=my_mover_turn, verbose=verbose)

                # move the mover to the destination
                yield from move_mover(environment, mover, destination, 'full', verbose=verbose)

                # unload the mover
                unloader.rate = unloader.unloading_func  # rate is variable to loading / unloading
                yield from shift_amount(environment, amount, unloader, mover, destination, origin_resource_request=my_mover_turn, verbose=verbose)

            activity_log.log_entry("transporting stop", environment.now, amount, mover.geometry)
        else:
            print('Nothing to move')
            yield environment.timeout(3600)


def shift_amount(environment, amount, processor, origin, destination, origin_resource_request=None, destination_resource_request=None, verbose=False):
        if id(origin) == id(processor) and origin_resource_request is not None or \
                id(destination) == id(processor) and destination_resource_request is not None:
            
            yield from processor.process(origin, destination, amount, origin_resource_request=origin_resource_request,
                                         destination_resource_request=destination_resource_request)
        else:
            with processor.resource.request() as my_processor_turn:
                yield my_processor_turn

                processor.log_entry('processing start', environment.now, amount, processor.geometry)
                yield from processor.process(origin, destination, amount,
                                             origin_resource_request=origin_resource_request,
                                             destination_resource_request=destination_resource_request)
                
                processor.log_entry('processing stop', environment.now, amount, processor.geometry)
                    
        if verbose == True:
            print('Processed {}:'.format(amount))
            print('  from:        ' + origin.name + ' contains: ' + str(origin.container.level))
            print('  by:          ' + processor.name)
            print('  to:          ' + destination.name + ' contains: ' + str(destination.container.level))


def move_mover(environment, mover, origin, status, verbose=False):
        old_location = mover.geometry

        mover.log_entry('sailing ' + status + ' start', environment.now, mover.container.level, mover.geometry)
        yield from mover.move(origin)
        mover.log_entry('sailing ' + status + ' stop', environment.now, mover.container.level, mover.geometry)

        if verbose == True:
            print('Moved:')
            print('  object:      ' + mover.name + ' contains: ' + str(mover.container.level))
            print('  from:        ' + format(old_location.x, '02.5f') + ' ' + format(old_location.y, '02.5f'))
            print('  to:          ' + format(mover.geometry.x, '02.5f') + ' ' + format(mover.geometry.y, '02.5f'))


class ActivityLog(core.Identifiable, core.Log):
    """A basic class that can be used to log activities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Simulation(core.Identifiable, core.Log):
    """The Simulation Class can be used to set up a full simulation using configuration dictionaries (json).

    sites:  a dictionary where the keys are the names the classes will have and the id associated with
            the constructed object (used to reference to the object in activities)
            the values are another dictionary containing the keys "name", "type" and "properties"
    equipment: a dictionary where the keys are the names the classes will have and the id associated with
            the constructed object (used to reference to the object in activities)
            the values are another dictionary containing the keys "name", "type" and "properties"
    activities: a dictionary where the keys are the names the activities logging will be reported under,
                the values are another dictionary containing the keys "origin", "destination", "loader",
                "mover", "unloader", each of these has a string value corresponding to the key of the site or
                equipment respectively. The keys given under "origin" and "destination" must be present in the
                "sites" parameter, the keys given for the "loader", "mover" and "unloader" must be present in the
                "equipment" parameter.
    decision_code: will probably be used to pass the "decision code" constructed through blockly in the future.
                   Has no effect for now.

    Each of the values the sites and equipment dictionaries, are another dictionary specifying "name",
    "type" and "properties". Here "name" is used to initialize the objects name (required by core.Identifiable).
    The "type" must be a list of mixin class names which will be used to construct a dynamic class for the
    object. For example: ["HasStorage", "HasResource", "Locatable"]. The core.Identifiable and core.Log class will
    always be added automatically by the Simulation class.
    The "properties" must be a dictionary which is used to construct the arguments for initializing the object.
    For example, if "HasContainer" is included in the "type" list, the "properties" dictionary must include a "capacity"
    which has the value that will be passed to the constructor of HasContainer. In this case, the "properties"
    dictionary can also optionally specify the "level".
    """

    def __init__(self, sites, equipment, activities, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__init_sites(sites)
        self.__init_equipment(equipment)
        self.__init_activities(activities)

    def __init_sites(self, sites):
        self.sites = {}
        for site in sites:
            self.sites[site['id']] = self.__init_object_from_json(site)

    def __init_equipment(self, equipment):
        self.equipment = {}
        for equipment_piece in equipment:
            self.equipment[equipment_piece['id']] = self.__init_object_from_json(equipment_piece)

    def __init_activities(self, activities):
        self.activities = {}
        for activity in activities:
            id = activity['id']
            type = activity['type']

            activity_log = ActivityLog(env=self.env, name=id)

            if type == 'move':
                mover = self.equipment[activity['mover']]
                destination = self.sites[activity['destination']]
                process = self.env.process(self.move_process_control(activity_log, mover, destination))
            elif type == 'single_run':
                pass  # todo
            elif type == 'conditional_run':
                pass  # todo
            else:
                raise RuntimeError('Unrecognized activity type: ' + type)

            self.activities[id] = {
                "activity_log": activity_log,
                "process": process
            }

    def move_process_control(self, activity_log, mover, destination):
        activity_log.log_entry('started move activity of {} to {}'.format(mover.name, destination.name),
                               self.env.now, -1, mover.geometry)

        yield from mover.move(destination)

        activity_log.log_entry('completed move activity of {} to {}'.format(mover.name, destination.name),
                               self.env.now, -1, mover.geometry)

    def single_run_process_control(self, activity_log, origin, destination, loader, mover, unloader):
        pass  # todo

    def conditional_process_control(self, activity_log, condition, activities):
        pass  # todo

    def __init_object_from_json(self, object_json):
        class_name = object_json["id"]
        name = object_json["name"]
        type = object_json["type"]
        properties = object_json["properties"]

        klass = get_class_from_type_list(class_name, type)
        kwargs = get_kwargs_from_properties(self.env, name, properties, self.sites)

        new_object = klass(**kwargs)

        add_object_properties(new_object, properties)

        return new_object

    def get_logging(self):
        json = {"simulation": self.get_log_as_json()}

        sites_logging = {}
        for key, site in self.sites.items():
            sites_logging[key] = site.get_log_as_json()
        json["sites"] = sites_logging

        equipment_logging = {}
        for key, equipment in self.equipment.items():
            equipment_logging[key] = equipment.get_log_as_json()
        json["equipment"] = equipment_logging

        activity_logging = {}
        for key, activity in self.activities.items():
            activity_logging[key] = activity["activity_log"].get_log_as_json()
        json["activities"] = activity_logging

        return json


def get_class_from_type_list(class_name, type_list):
    mixin_classes = [core.Identifiable, core.Log] + [string_to_class(text) for text in type_list]
    return type(class_name, tuple(mixin_classes), {})


def string_to_class(text):
    # quick hack to get the classes, there is probably a better way...
    class_dict = {
        "Locatable": core.Locatable,
        "HasContainer": core.HasContainer,
        "EnergyUse": core.EnergyUse,
        "HasPlume": core.HasPlume,
        "HasSpillCondition": core.HasSpillCondition,
        "HasSpill": core.HasSpill,
        "HasSoil": core.HasSoil,
        "HasWeather": core.HasWeather,
        "HasWorkabilityCriteria": core.HasWorkabilityCriteria,
        "HasDepthRestriction": core.HasDepthRestriction,
        "Routable": core.Routeable,
        "Movable": core.Movable,
        "ContainerDependentMovable": core.ContainerDependentMovable,
        "HasResource": core.HasResource,
        "Processor": core.Processor
    }
    return class_dict[text]


def get_kwargs_from_properties(environment, name, properties, sites):
    kwargs = {
        "env": environment,
        "name": name
    }

    # some checks on the configuration could be added here,
    # for example, if both level and capacity are given, is level <= capacity, level >= 0, capacity >= 0 etc.
    # for compute functions:
    # - check if there are enough entries for interp1d / interp2d,
    # - check if functions of for example level have a range from 0 to max level (capacity)

    # Locatable
    if "geometry" in properties:
        kwargs["geometry"] = shapely.geometry.asShape(properties["geometry"]).centroid
    if "location" in properties:
        kwargs["geometry"] = sites[properties["location"]].geometry

    # HasContainer
    if "capacity" in properties:
        kwargs["capacity"] = properties["capacity"]
    if "level" in properties:
        kwargs["level"] = properties["level"]

    # EnergyUse
    if "energy_use_sailing" in properties:
        pass # todo
    if "energy_use_loading" in properties:
        pass # todo
    if "energy_use_unloading" in properties:
        pass # todo

    # HasPlume
    if "sigma_d" in properties:
        kwargs["sigma_d"] = properties["sigma_d"]
    if "sigma_o" in properties:
        kwargs["sigma_o"] = properties["sigma_o"]
    if "sigma_p" in properties:
        kwargs["sigma_p"] = properties["sigma_p"]
    if "f_sett" in properties:
        kwargs["f_sett"] = properties["f_sett"]
    if "f_trap" in properties:
        kwargs["f_trap"] = properties["f_trap"]

    # HasSpillCondition
    if "conditions" in properties:
        condition_list = properties["conditions"]
        condition_objects = [core.SpillCondition(**get_spill_condition_kwargs(environment, condition_dict))
                             for condition_dict in condition_list]
        kwargs["conditions"] = condition_objects

    # HasWeather
    if "file" in properties:
        # todo fix file location, how is this passed to the server? always use same fake weather file?
        kwargs["file"] = properties["file"]
    if "year" in properties:
        kwargs["year"] = properties["year"]
    if "month" in properties:
        kwargs["month"] = properties["month"]
    if "day" in properties:
        kwargs["day"] = properties["day"]
    if "hour" in properties:
        kwargs["hour"] = properties["hour"]
    if "timestep" in properties:
        kwargs["timestep"] = properties["timestep"]
    if "bed" in properties:
        kwargs["bed"] = properties["bed"]

    # HasWorkabilityCriteria
    # todo Movable has the same parameter v, so this value might be overwritten by speed!
    if "v" in properties:
        kwargs["v"] = properties["v"]

    # HasDepthRestriction
    if "draught" in properties:
        kwargs["compute_draught"] = get_compute_function(properties["draught"], "level", "draught")
    if "waves" in properties:
        kwargs["waves"] = properties["waves"]
    if "ukc" in properties:
        kwargs["ukc"] = properties["ukc"]

    # Routable arguments: route -> todo figure out how this would appear in properties and can be parsed into kwargs

    # ContainerDependentMovable & Movable
    if "speed" in properties:
        speed = properties["speed"]
        if isinstance(speed, list):
            kwargs["compute_v"] = get_compute_function(speed, "level", "speed")
        else:
            kwargs["v"] = speed

    # HasResource
    if "nr_resources" in properties:
        kwargs["nr_resources"] = properties["nr_resources"]

    # Processor
    if "loading_rate" in properties:
        kwargs["loading_func"] = get_rate_compute_function(properties["loading_rate"])
    if "unloading_rate" in properties:
        kwargs["unloading_func"] = get_rate_compute_function(properties["unloading_rate"])

    return kwargs


def add_object_properties(new_object, properties):
    # HasSoil
    if "layers" in properties:
        layer_list = properties["layers"]
        layer_objects = [core.SoilLayer(i, **layer_dict) for i, layer_dict in enumerate(layer_list)]
        new_object.add_layers(layer_objects)


def get_spill_condition_kwargs(environment, condition_dict):
    kwargs = {}
    kwargs["spill_limit"] = condition_dict["limit"]

    initial_time = datetime.datetime.fromtimestamp(environment.now)

    kwargs["start"] = initial_time + datetime.timedelta(days=condition_dict["start"])
    kwargs["end"] = initial_time + datetime.timedelta(days=condition_dict["end"])
    return kwargs


def get_compute_function(table_entry_list, x_key, y_key):
    df = pd.DataFrame(table_entry_list)
    return scipy.interpolate.interp1d(df[x_key], df[y_key])


def get_rate_compute_function(property):
    if isinstance(property, list):
        # given property is a list of data points
        rate_function = get_compute_function(property, "level", "rate")
        inversed_rate_function = lambda x: 1 / rate_function(x)
        # assumes the container is empty at the start of loading!
        return lambda x: scipy.integrate.quad(inversed_rate_function, 0, x)[0]
    else:
        # given property is a flat rate
        return lambda x: x / property
