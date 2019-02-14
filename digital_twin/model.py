from functools import partial
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


def perform_single_run(environment, activity_log, origin, destination, loader, mover, unloader, engine_order=1.0, filling=1.0, verbose=False):
        """Installation process"""
        # estimate amount that should be transported
        amount = min(
            mover.container.capacity * filling - mover.container.level,
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
                    yield from move_mover(mover, origin, engine_order=engine_order, verbose=verbose)

                # load the mover
                yield from shift_amount(environment, loader, mover, mover.container.level + amount, origin, ship_resource_request=my_mover_turn, verbose=verbose)

                # move the mover to the destination
                yield from move_mover(mover, destination, engine_order=engine_order, verbose=verbose)

                # unload the mover
                yield from shift_amount(environment, unloader, mover, mover.container.level - amount, destination, ship_resource_request=my_mover_turn, verbose=verbose)

            activity_log.log_entry("transporting stop", environment.now, amount, mover.geometry)
        else:
            print('Nothing to move')
            yield environment.timeout(3600)


def shift_amount(environment, processor, ship, desired_level, site, ship_resource_request=None, site_resource_request=None, verbose=False):
    amount = np.abs(ship.container.level - desired_level)

    if id(ship) == id(processor) and ship_resource_request is not None or \
            id(site) == id(processor) and site_resource_request is not None:

        yield from processor.process(ship, desired_level, site, ship_resource_request=ship_resource_request,
                                     site_resource_request=site_resource_request)
    else:
        with processor.resource.request() as my_processor_turn:
            yield my_processor_turn

            processor.log_entry('processing start', environment.now, amount, processor.geometry)
            yield from processor.process(ship, desired_level, site,
                                         ship_resource_request=ship_resource_request,
                                         site_resource_request=site_resource_request)

            processor.log_entry('processing stop', environment.now, amount, processor.geometry)

    if verbose == True:
        print('Processed {}:'.format(amount))
        print('  by:          ' + processor.name)
        print('  ship:        ' + ship.name + ' contains: ' + str(ship.container.level))
        print('  site:        ' + site.name + ' contains: ' + str(site.container.level))


def move_mover(mover, origin, engine_order=1.0, verbose=False):
        old_location = mover.geometry

        yield from mover.move(origin, engine_order=engine_order)

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

    sites:  a list of dictionaries specifying which site objects should be constructed
    equipment: a list of dictionaries specifying which equipment objects should be constructed
    activities: list of dictionaries specifying which activities should be performed during the simulation

    Each of the values the sites and equipment lists, are a dictionary specifying "id", "name",
    "type" and "properties". Here "id" can be used to refer to this site / equipment in other parts of the
    configuration, "name" is used to initialize the objects name (required by core.Identifiable).
    The "type" must be a list of mixin class names which will be used to construct a dynamic class for the
    object. For example: ["HasStorage", "HasResource", "Locatable"]. The core.Identifiable and core.Log class will
    always be added automatically by the Simulation class.
    The "properties" must be a dictionary which is used to construct the arguments for initializing the object.
    For example, if "HasContainer" is included in the "type" list, the "properties" dictionary must include a "capacity"
    which has the value that will be passed to the constructor of HasContainer. In this case, the "properties"
    dictionary can also optionally specify the "level".

    Each of the values of the activities list, is a dictionary specifying an "id", "type", and other fields depending
    on the type. The supported types are "move", "single_run", and "conditional".
    For a "move" type activity, the dictionary should also contain a "mover", "destination" and can optionally contain
    a "moverProperties" dictionary containing an "engineOrder".
    For a "single_run" type activity, the dictionary should also contain an "origin", "destination", "loader", "mover",
    "unloader" and can optionally contain a "moverProperties" dictionary containing an "engineOrder" and/or "load".
    For a "conditional" type activity, the dictionary should also contain a "condition" and "activities", where the
    "activities" is another list of activities which will be performed while the condition is true.
    The "condition" of a "conditional" type activity is a dictionary containing an "operator" and an "operand". The
    operator can be "is_full", "is_filled" or "is_empty". The "operand" must be the id of the object (site or equipment)
    of which the container level will be checked on if it is full (equal to capacity), filled (greater than 0) or empty
    (equal to 0) respectively.
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
            activity_log = ActivityLog(env=self.env, name=id)

            process = self.env.process(self.get_process_control(activity_log, activity))

            self.activities[id] = {
                "activity_log": activity_log,
                "process": process
            }

    def get_process_control(self, activity_log, activity):
        type = activity['type']

        if type == 'move':
            mover = self.equipment[activity['mover']]
            kwargs = self.get_mover_properties_kwargs(activity)
            destination = self.sites[activity['destination']]
            return self.move_process_control(activity_log, mover, destination, **kwargs)
        if type == 'single_run':
            mover = self.equipment[activity['mover']]
            kwargs = self.get_mover_properties_kwargs(activity)
            origin = self.sites[activity['origin']]
            destination = self.sites[activity['destination']]
            loader = self.equipment[activity['loader']]
            unloader = self.equipment[activity['unloader']]
            return self.single_run_process_control(activity_log, origin, destination, loader, mover, unloader, **kwargs)
        if type == 'conditional':
            condition = activity['condition']
            activities = activity['activities']
            return self.conditional_process_control(activity_log, condition, activities)
        else:
            raise RuntimeError('Unrecognized activity type: ' + type)

    @staticmethod
    def get_mover_properties_kwargs(activity):
        if "moverProperties" not in activity:
            return {}

        kwargs = {}
        mover_options = activity["moverProperties"]
        if "engineOrder" in mover_options:
            kwargs["engine_order"] = mover_options["engineOrder"]
        if "load" in mover_options:
            kwargs["filling"] = mover_options["load"]

        return kwargs

    def move_process_control(self, activity_log, mover, destination, **kwargs):
        activity_log.log_entry('started move activity of {} to {}'.format(mover.name, destination.name),
                               self.env.now, -1, mover.geometry)

        with mover.resource.request() as my_mover_turn:
            yield my_mover_turn
            yield from mover.move(destination, **kwargs)

        activity_log.log_entry('completed move activity of {} to {}'.format(mover.name, destination.name),
                               self.env.now, -1, mover.geometry)

    def single_run_process_control(self, activity_log, origin, destination, loader, mover, unloader, **kwargs):
        activity_description = 'single_run activity loading {} at {} with {} ' \
                               'and transporting to {} unloading with {}'\
                               .format(mover.name, origin.name, loader.name, destination.name, unloader.name)
        activity_log.log_entry('started ' + activity_description, self.env.now, -1, mover.geometry)

        yield from perform_single_run(self.env, activity_log, origin, destination, loader, mover, unloader, **kwargs)

        activity_log.log_entry('completed ' + activity_description, self.env.now, -1, mover.geometry)

    def conditional_process_control(self, activity_log, condition, activities):
        condition_checker = self.get_condition_checker(condition)

        while condition_checker():
            for activity in activities:
                yield from self.get_process_control(activity_log, activity)

    def get_condition_checker(self, condition):
        operator = condition['operator']
        operand_key = condition['operand']
        operand = self.sites[operand_key] if operand_key in self.sites else self.equipment[operand_key]

        if operator == 'is_full':
            return lambda: operand.container.level == operand.container.capacity
        elif operator == 'is_filled':
            return lambda: operand.container.level > 0
        elif operator == 'is_empty':
            return lambda: operand.container.level == 0
        else:
            raise RuntimeError('Unrecognized operator type: ' + operator)

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
        json = {}

        sites_logging = []
        for key, site in self.sites.items():
            sites_logging.append(
                self.get_as_feature_collection(key, site.get_log_as_json())
            )
        json["sites"] = sites_logging

        equipment_logging = []
        for key, equipment in self.equipment.items():
            equipment_logging.append(
                self.get_as_feature_collection(key, equipment.get_log_as_json())
            )
        json["equipment"] = equipment_logging

        activity_logging = []
        for key, activity in self.activities.items():
            activity_logging.append(
                self.get_as_feature_collection(key, activity["activity_log"].get_log_as_json())
            )
        json["activities"] = activity_logging

        return json

    @staticmethod
    def get_as_feature_collection(id, features):
        return dict(
            type="FeatureCollection",
            id=id,
            features=features
        )


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
    if "weather" in properties:
        df = pd.DataFrame(properties["weather"])
        df.index = df["time"].apply(datetime.datetime.fromtimestamp)
        df = df.drop(columns=["time"])
        kwargs["dataframe"] = df.rename(columns={"tide": "Tide", "hs": "Hs"})
    if "bed" in properties:
        kwargs["bed"] = properties["bed"]

    # HasWorkabilityCriteria
    # todo Movable has the same parameter v, so this value might be overwritten by speed!
    if "v" in properties:
        kwargs["v"] = properties["v"]

    # HasDepthRestriction
    if "draught" in properties:
        df = pd.DataFrame(properties["draught"])
        df["filling_degree"] = df["level"] / kwargs["capacity"]
        kwargs["compute_draught"] = scipy.interpolate.interp1d(df["filling_degree"], df["draught"])
    if "waves" in properties:
        kwargs["waves"] = properties["waves"]
    if "ukc" in properties:
        kwargs["ukc"] = properties["ukc"]

    # Routable arguments: route -> todo figure out how this would appear in properties and can be parsed into kwargs

    # ContainerDependentMovable & Movable
    if "speed" in properties:
        speed = properties["speed"]
        if isinstance(speed, list):
            df = pd.DataFrame(speed)
            df["filling_degree"] = df["level"] / kwargs["capacity"]
            compute_function = scipy.interpolate.interp1d(df["filling_degree"], df["speed"])
            kwargs["compute_v"] = compute_function
            v_empty = compute_function(0)
            v_full = compute_function(1)
        else:
            kwargs["v"] = speed
            v_empty = speed
            v_full = speed

        # EnergyUse
        if "energyUseSailing" in properties:
            energy_use_sailing_dict = properties["energyUseSailing"]
            max_propulsion = energy_use_sailing_dict["maxPropulsion"]
            boardnet = energy_use_sailing_dict["boardnet"]
            kwargs["energy_use_sailing"] = partial(energy_use_sailing,
                                                   speed_max_full=v_full,
                                                   speed_max_empty=v_empty,
                                                   propulsion_power_max=max_propulsion,
                                                   boardnet_power=boardnet)

    # EnergyUse
    if "energyUseLoading" in properties:
        kwargs["energy_use_loading"] = partial(energy_use_processing, constant_hourly_use=properties["energyUseLoading"])
    if "energyUseUnloading" in properties:
        kwargs["energy_use_unloading"] = partial(energy_use_processing, constant_hourly_use=properties["energyUseUnloading"])

    # HasResource
    if "nr_resources" in properties:
        kwargs["nr_resources"] = properties["nr_resources"]

    # Processor
    if "loadingRate" in properties:
        kwargs["loading_func"] = get_loading_func(properties["loadingRate"])
    if "unloadingRate" in properties:
        kwargs["unloading_func"] = get_unloading_func(properties["unloadingRate"])

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


def get_loading_func(property):
    """Returns a loading_func based on the given input property.
    Input can be a flat rate or a table defining the rate depending on the level.
    In the second case, note that by definition the rate is the derivative of the level with respect to time.
    Therefore d level / dt = f(level), from which we can obtain that the time taken for loading can be calculated
    by integrating 1 / f(level) from current_level to desired_level."""
    if isinstance(property, list):
        # given property is a list of data points
        rate_function = get_compute_function(property, "level", "rate")
        inversed_rate_function = lambda x: 1 / rate_function(x)
        return lambda current_level, desired_level: \
            scipy.integrate.quad(inversed_rate_function, current_level, desired_level)[0]
    else:
        # given property is a flat rate
        return lambda current_level, desired_level: (desired_level - current_level) / property


def get_unloading_func(property):
    """Returns an unloading_funct based on the given input property.
    Input can be a flat rate or a table defining the rate depending on the level.
    In the second case, note that by definition the rate is -1 times the derivative of the level with respect to time.
    Therefore d level / dt = - f(level), from which we can obtain the the time taken for unloading can be calculated
    by integrating 1 / f(level) from desired_level to current_level."""
    if isinstance(property, list):
        # given property is a list of data points
        rate_function = get_compute_function(property, "level", "rate")
        inversed_rate_function = lambda x: 1 / rate_function(x)
        return lambda current_level, desired_level: \
            scipy.integrate.quad(inversed_rate_function, desired_level, current_level)[0]
    else:
        # given property is a flat rate
        return lambda current_level, desired_level: (current_level - desired_level) / property


def energy_use_sailing(distance, current_speed, filling_degree, speed_max_full, speed_max_empty,
                       propulsion_power_max, boardnet_power):
    duration_seconds = distance / current_speed
    duration_hours = duration_seconds / 3600
    speed_factor_full = current_speed / speed_max_full
    speed_factor_empty = current_speed / speed_max_empty
    energy_use_sailing_full = duration_hours * (speed_factor_full ** 3 * propulsion_power_max + boardnet_power * 0.6)
    energy_use_sailing_empty = duration_hours * (speed_factor_empty ** 3 * propulsion_power_max + boardnet_power * 0.6)
    return filling_degree * (energy_use_sailing_full - energy_use_sailing_empty) + energy_use_sailing_empty


def energy_use_processing(duration_seconds, constant_hourly_use):
    duration_hours = duration_seconds / 3600
    return duration_hours * constant_hourly_use
