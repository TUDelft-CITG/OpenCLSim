from functools import partial
import itertools
import openclsim.core as core
import datetime
import simpy
import shapely
import shapely.geometry
import scipy.interpolate
import scipy.integrate
import pandas as pd
import numpy as np


class Activity(core.Identifiable, core.Log):
    """The Activity Class forms a specific class for a single activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

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
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        origin,
        destination,
        loader,
        mover,
        unloader,
        start_event=None,
        stop_event=None,
        show=False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.origin = origin if origin == type(list) else [origin]
        self.destination = destination if destination == type(list) else [destination]

        self.start_event = (
            start_event
            if start_event is None or isinstance(start_event, simpy.Event)
            else self.env.all_of(events=start_event)
        )

        if type(stop_event) == list:
            stop_event = self.env.any_of(events=stop_event)

        if not start_event and stop_event is not None:
            self.stop_event = stop_event

        elif not start_event:
            stop_event = []
            stop_event.extend(orig.container.empty_event for orig in self.origin)
            stop_event.extend(dest.container.full_event for dest in self.destination)
            self.stop_event = self.env.any_of(stop_event)

        else:
            stop_event = []
            stop_event.extend(orig.container.get_empty_event for orig in self.origin)
            stop_event.extend(
                dest.container.get_full_event for dest in self.destination
            )
            self.stop_event = self.env.any_of(stop_event)

        self.stop_reservation_waiting_event = (
            self.stop_event()
            if hasattr(self.stop_event, "__call__")
            else self.stop_event
        )

        self.origin = origin
        self.destination = destination
        self.loader = loader
        self.mover = mover
        self.unloader = unloader
        self.print = show

        origin, destination = optimise_production(
            origin, destination, loader, mover, unloader, 1, 1
        )

        single_run_proc = partial(
            single_run_process,
            origin=origin,
            destination=destination,
            loader=loader,
            mover=mover,
            unloader=unloader,
            stop_reservation_waiting_event=self.stop_reservation_waiting_event,
            verbose=self.print,
        )
        main_proc = partial(
            conditional_process,
            stop_event=self.stop_event,
            sub_processes=[single_run_proc],
        )
        if start_event is not None:
            main_proc = partial(
                delayed_process, start_event=self.start_event, sub_processes=[main_proc]
            )
        self.main_process = self.env.process(main_proc(activity_log=self, env=self.env))


def determine_amount(origin, destination, loader, mover, unloader, filling):
    """ Determine the maximum amount that can be carried """

    # Determine the basic amount that should be transported
    all_amounts = {}
    all_amounts.update({"origin." + orig.id: orig.container.expected_level for orig in origin})
    all_amounts.update({"destination." + dest.id: dest.container.capacity - dest.container.expected_level for dest in destination})
    
    origin_requested = 0
    destination_requested = 0

    for key in all_amounts.keys():
        if "origin." in key:
            origin_requested += all_amounts[key]
        else:
            destination_requested += all_amounts[key]
    
    amount = min(
        mover.container.capacity * filling - mover.container.level,
        origin_requested,
        destination_requested,
    )

    # If the mover has a function to optimize its load, check if the amount should be changed
    if not hasattr(mover, "check_optimal_filling"):
        return amount, all_amounts

    else:
        return min(
            amount, mover.check_optimal_filling(loader, unloader, origin, destination)
        )


def determine_duration(
    origin, destination, loader, mover, unloader, amount, engine_order
):
    """ Determine the duration of a trip """

    duration = 0
    duration += mover.sailing_duration(mover.geometry, origin, engine_order)
    duration += loader.loading(origin, mover, amount)
    duration += mover.sailing_duration(
        origin.geometry, destination.geometry, engine_order
    )
    duration += unloader.unloading(mover, destination, amount)
    duration += mover.sailing_duration(
        destination.geometry, origin.geometry, engine_order
    )

    return duration


def optimise_production(
    origin, destination, loader, mover, unloader, filling, engine_order
):
    """ Select origin and destination to optimise trip production """

    if type(origin) != list and type(destination) != list:
        return origin, destination

    elif type(origin) != list:
        origin = [origin]
    elif type(destination) != list:
        destination = [destination]

    optimal_production = 0

    for orig, dest in itertools.product(origin, destination):
        amount = determine_amount(orig, dest, loader, mover, unloader, filling)
        duration = determine_duration(
            orig, dest, loader, mover, unloader, amount, engine_order
        )

        if optimal_production < amount / duration:
            optimal_origin = orig
            optimal_destination = dest

    return optimal_origin, optimal_destination


def delayed_process(activity_log, env, start_event, sub_processes):
    """"Returns a generator which can be added as a process to a simpy.Environment. In the process the given
    sub_processes will be executed after the given start_event occurs.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
    start_event: a simpy.Event object, when this event occurs the delayed process will start executing its sub_processes
    sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                   return a generator which could be added as a process to a simpy.Environment
                   the sub_processes will be executed sequentially, in the order in which they are given after the
                   start_event occurs
    """
    if hasattr(start_event, "__call__"):
        start_event = start_event()

    yield start_event
    activity_log.log_entry(
        "delayed activity started", env.now, -1, None, activity_log.id
    )

    for sub_process in sub_processes:
        yield from sub_process(activity_log=activity_log, env=env)


def conditional_process(activity_log, env, stop_event, sub_processes):
    """Returns a generator which can be added as a process to a simpy.Environment. In the process the given
    sub_processes will be executed until the given stop_event occurs. If the stop_event occurs during the execution
    of the sub_processes, the conditional process will first complete all sub_processes (which are executed sequentially
    in the order in which they are given), before finishing its own process.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
    stop_event: a simpy.Event object, when this event occurs, the conditional process will finish executing its current
                run of its sub_processes and then finish
    sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                   return a generator which could be added as a process to a simpy.Environment
                   the sub_processes will be executed sequentially, in the order in which they are given as long
                   as the stop_event has not occurred.
    """

    if activity_log.log["Message"]:
        if activity_log.log["Message"][-1] == "delayed activity started" and hasattr(
            stop_event, "__call__"
        ):
            stop_event = stop_event()

    if hasattr(stop_event, "__call__"):
        stop_event = stop_event()
    elif type(stop_event) == list:
        stop_event = env.any_of(events=[event() for event in stop_event])

    while not stop_event.processed:
        for sub_process in sub_processes:
            yield from sub_process(activity_log=activity_log, env=env)

    activity_log.log_entry("stopped", env.now, -1, None, activity_log.id)


def sequential_process(activity_log, env, sub_processes):
    """Returns a generator which can be added as a process to a simpy.Environment. In the process the given
    sub_processes will be executed sequentially in the order in which they are given.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
    sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                   return a generator which could be added as a process to a simpy.Environment
                   the sub_processes will be executed sequentially, in the order in which they are given
    """
    activity_log.log_entry("sequential start", env.now, -1, None, activity_log.id)
    for sub_process in sub_processes:
        yield from sub_process(activity_log=activity_log, env=env)
    activity_log.log_entry("sequential stop", env.now, -1, None, activity_log.id)


def move_process(activity_log, env, mover, destination, engine_order=1.0):
    """Returns a generator which can be added as a process to a simpy.Environment. In the process, a move will be made
    by the mover, moving it to the destination.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
    mover: moves from its current position to the destination
           should inherit from core.Movable
    destination: the location the mover will move to
                 should inherit from core.Locatable
    engine_order: optional parameter specifying at what percentage of the maximum speed the mover should sail.
                  for example, engine_order=0.5 corresponds to sailing at 50% of max speed
    """
    activity_log.log_entry(
        "started move activity of {} to {}".format(mover.name, destination.name),
        env.now,
        -1,
        mover.geometry,
        activity_log.id,
    )

    with mover.resource.request() as my_mover_turn:
        yield my_mover_turn

        mover.ActivityID = activity_log.id
        yield from mover.move(destination=destination, engine_order=engine_order)

    activity_log.log_entry(
        "completed move activity of {} to {}".format(mover.name, destination.name),
        env.now,
        -1,
        mover.geometry,
        activity_log.id,
    )


def single_run_process(
    activity_log,
    env,
    origin,
    destination,
    loader,
    mover,
    unloader,
    engine_order=1.0,
    filling=1.0,
    stop_reservation_waiting_event=None,
    verbose=False,
):
    """Returns a generator which can be added as a process to a simpy.Environment. In the process, a single run will
    be made by the given mover, transporting content from the origin to the destination.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
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
    engine_order: optional parameter specifying at what percentage of the maximum speed the mover should sail.
                  for example, engine_order=0.5 corresponds to sailing at 50% of max speed
    filling: optional parameter specifying at what percentage of the maximum capacity the mover should be loaded.
             for example, filling=0.5 corresponds to loading the mover up to 50% of its capacity
    stop_reservation_waiting_event: a simpy.Event, if there is no content available in the origin, or no space available
                                    in the destination, instead of performing a single run, the process will wait for
                                    new content or space to become available. If a stop_reservation_waiting_event is
                                    passed, this event will be combined through a simpy.AnyOf event with the event
                                    occurring when new content or space becomes available. This can be used to prevent
                                    waiting for new content or space indefinitely when we know it will not become
                                    available.
    verbose: optional boolean indicating whether additional debug prints should be given.
    """

    # Required for logging from json
    if not hasattr(activity_log, "loader"):
        activity_log.loader = loader
    if not hasattr(activity_log, "mover"):
        activity_log.mover = mover
    if not hasattr(activity_log, "unloader"):
        activity_log.unloader = unloader

    amount, all_amounts = determine_amount(origin, destination, loader, mover, unloader, filling)

    # Check if activity can start
    if hasattr(stop_reservation_waiting_event, "__call__"):
        stop_reservation_waiting_event = stop_reservation_waiting_event()
    elif type(stop_reservation_waiting_event) == list:
        stop_reservation_waiting_event = env.any_of(
            events=[event() for event in stop_reservation_waiting_event]
        )

    # If the transported amount is larger than zero, start activity
    if 0 < amount:
        resource_requests = {}
        vrachtbrief = {}

        to_retrieve = 0
        to_place = 0

        # reserve the amount in origin an destination
        for orig in origin:
            if all_amounts[orig.id] <= amount - to_retrieve:
                to_retrieve += all_amounts[orig.id]
                vrachtbrief[orig.id] = all_amounts[orig.id]
                orig.container.reserve_get(all_amounts[orig.id])

            else:
                orig.container.reserve_get(amount - to_retrieve)
                vrachtbrief[orig.id] = amount - to_retrieve
                break

        for dest in destination:
            if all_amounts[dest.id] <= amount - to_place:
                to_place += all_amounts[orig.id]
                vrachtbrief[dest.id] = all_amounts[dest.id]
                dest.container.reserve_put(all_amounts[dest.id])

            else:
                dest.container.reserve_put(amount - to_place)
                break

        if verbose:
            print("Using " + mover.name + " to process " + str(amount))
        activity_log.log_entry(
            "transporting start", env.now, amount, mover.geometry, activity_log.id
        )

        # request the mover's resource
        yield from _request_resource(resource_requests, mover.resource)

        for orig in origin:
            if orig.id in vrachtbrief.keys():
                
                # move the mover to the origin (if necessary)
                if not mover.is_at(origin):
                    yield from _move_mover(
                        mover,
                        origin,
                        ActivityID=activity_log.id,
                        engine_order=engine_order,
                        verbose=verbose,
                    )

                yield from _request_resources_if_transfer_possible(
                    env,
                    resource_requests,
                    origin,
                    loader,
                    mover,
                    vrachtbrief[dest.id],
                    mover.resource,
                    activity_log.id,
                    engine_order=engine_order,
                    verbose=verbose,
                )

                # load the mover
                yield from _shift_amount(
                    env,
                    loader,
                    mover,
                    mover.container.level + vrachtbrief[dest.id],
                    origin,
                    ActivityID=activity_log.id,
                    verbose=verbose,
                )

                # release the loader and origin resources (but always keep the mover requested)
                _release_resource(
                    resource_requests, loader.resource, kept_resource=mover.resource
                )
                _release_resource(
                    resource_requests, orig.resource, kept_resource=mover.resource
                )

        for dest in destination:
            if dest.id in vrachtbrief.keys():

                # move the mover to the destination
                if not mover.is_at(destination):
                    yield from _move_mover(
                        mover,
                        destination,
                        ActivityID=activity_log.id,
                        engine_order=engine_order,
                        verbose=verbose,
                    )

                yield from _request_resources_if_transfer_possible(
                    env,
                    resource_requests,
                    mover,
                    unloader,
                    destination,
                    vrachtbrief[dest.id],
                    mover.resource,
                    activity_log.id,
                    engine_order=engine_order,
                    verbose=verbose,
                )

                # unload the mover
                yield from _shift_amount(
                    env,
                    unloader,
                    mover,
                    mover.container.level - vrachtbrief[dest.id],
                    destination,
                    ActivityID=activity_log.id,
                    verbose=verbose,
                )

                # release the unloader, destination and mover requests
                _release_resource(resource_requests, unloader.resource)
                if dest.resource in resource_requests:
                    _release_resource(resource_requests, dest.resource)
                if mover.resource in resource_requests:
                    _release_resource(resource_requests, mover.resource)

        activity_log.log_entry(
            "transporting stop", env.now, amount, mover.geometry, activity_log.id
        )
    else:
        if origin.container.expected_level == 0:
            activity_log.log_entry(
                "waiting origin reservation start",
                env.now,
                origin.container.expected_level,
                origin.geometry,
                activity_log.id,
            )
            yield _or_optional_event(
                env,
                origin.container.reserve_get_available,
                stop_reservation_waiting_event,
            )
            activity_log.log_entry(
                "waiting origin reservation stop",
                env.now,
                origin.container.expected_level,
                origin.geometry,
                activity_log.id,
            )
        elif destination.container.expected_level == destination.container.capacity:
            activity_log.log_entry(
                "waiting destination reservation start",
                env.now,
                destination.container.expected_level,
                destination.geometry,
                activity_log.id,
            )
            yield _or_optional_event(
                env,
                destination.container.reserve_put_available,
                stop_reservation_waiting_event,
            )
            activity_log.log_entry(
                "waiting destination reservation stop",
                env.now,
                destination.container.expected_level,
                destination.geometry,
                activity_log.id,
            )
        elif mover.container.level == mover.container.capacity:
            activity_log.log_entry(
                "waiting mover to finish start",
                env.now,
                mover.container.capacity,
                mover.geometry,
                activity_log.id,
            )

            yield env.timeout(3600)

            activity_log.log_entry(
                "waiting mover to finish stop",
                env.now,
                mover.container.capacity,
                mover.geometry,
                activity_log.id,
            )

        else:
            print(origin.log)
            print(origin.name, origin.container.level)
            print(
                mover.name,
                mover.container.level,
                mover.container.capacity,
                mover.container.expected_level,
            )
            print(destination.name, destination.container.level)
            raise RuntimeError("Attempting to move content with a full ship")


def _or_optional_event(env, event, optional_event):
    """If the optional_event is None, the event is returned. Otherwise the event and optional_event are combined
    through an any_of event, thus returning an event that will trigger if either of these events triggers.
    Used by single_run_process to combine an event used to wait for a reservation to become available with its
    optional stop_reservation_waiting_event."""
    if optional_event is None:
        return event
    return env.any_of(events=[event, optional_event])


def _request_resource(requested_resources, resource):
    """Requests the given resource and yields it.
    """
    if resource not in requested_resources:
        requested_resources[resource] = resource.request()
        yield requested_resources[resource]


def _release_resource(requested_resources, resource, kept_resource=None):
    """Releases the given resource, provided it does not equal the kept_resource parameter.
    Deletes the released resource from the requested_resources dictionary."""
    if resource != kept_resource:
        resource.release(requested_resources[resource])
        del requested_resources[resource]


def _shift_amount(env, processor, ship, desired_level, site, ActivityID, verbose=False):
    """Calls the processor.process method, giving debug print statements when verbose is True."""
    amount = np.abs(ship.container.level - desired_level)

    # Set ActivityID to processor and ship
    processor.ActivityID = ActivityID
    ship.ActivityID = ActivityID

    # Check if loading or unloading
    yield from processor.process(ship, desired_level, site)

    if verbose:
        print("Processed {}:".format(amount))
        print("  by:          " + processor.name)
        print("  ship:        " + ship.name + " contains: " + str(ship.container.level))
        print("  site:        " + site.name + " contains: " + str(site.container.level))


def _request_resources_if_transfer_possible(
    env,
    resource_requests,
    origin,
    processor,
    destination,
    amount,
    kept_resource,
    ActivityID,
    engine_order=1.0,
    verbose=False,
):
    """
    Sets up everything needed for single_run_process to shift an amount from the origin to the destination using
    the processor.process method.
    After yielding from this method:
     - the origin and destination contain a valid amount of content/space for the
       transferring of an amount to be possible
     - resource requests will have been added for the origin, destination and processor if they were not present already
     - the processor will be located at the origin if it was not already
    If during the yield to wait for space, content or a resource, some other process has caused the available space or
    content to be removed, all resource requests granted up to that point will be released and the method will restart
    the process of requesting space, content and resources. The passed "kept_resource" will never be released.
    """
    all_available = False
    while not all_available:
        # yield until enough content and space available in origin and destination
        yield env.all_of(
            events=[
                origin.container.get_available(amount),
                destination.container.put_available(amount),
            ]
        )

        yield from _request_resource(resource_requests, processor.resource)
        if (
            origin.container.level < amount
            or destination.container.capacity - destination.container.level < amount
        ):
            # someone removed / added content while we were requesting the processor, so abort and wait for available
            # space/content again
            _release_resource(
                resource_requests, processor.resource, kept_resource=kept_resource
            )
            continue

        if not processor.is_at(origin):
            # todo have the processor move simultaneously with the mover by starting a different process for it?
            yield from _move_mover(
                processor,
                origin,
                ActivityID=ActivityID,
                engine_order=engine_order,
                verbose=verbose,
            )
            if (
                origin.container.level < amount
                or destination.container.capacity - destination.container.level < amount
            ):
                # someone messed us up again, so return to waiting for space/content
                _release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                continue

        yield from _request_resource(resource_requests, origin.resource)
        if (
            origin.container.level < amount
            or destination.container.capacity - destination.container.level < amount
        ):
            _release_resource(
                resource_requests, processor.resource, kept_resource=kept_resource
            )
            _release_resource(
                resource_requests, origin.resource, kept_resource=kept_resource
            )
            continue

        yield from _request_resource(resource_requests, destination.resource)
        if (
            origin.container.level < amount
            or destination.container.capacity - destination.container.level < amount
        ):
            _release_resource(
                resource_requests, processor.resource, kept_resource=kept_resource
            )
            _release_resource(
                resource_requests, origin.resource, kept_resource=kept_resource
            )
            _release_resource(
                resource_requests, destination.resource, kept_resource=kept_resource
            )
            continue
        all_available = True


def _move_mover(mover, origin, ActivityID, engine_order=1.0, verbose=False):
    """Calls the mover.move method, giving debug print statements when verbose is True."""
    old_location = mover.geometry

    # Set ActivityID to mover
    mover.ActivityID = ActivityID
    yield from mover.move(origin, engine_order=engine_order)

    if verbose:
        print("Moved:")
        print(
            "  object:      " + mover.name + " contains: " + str(mover.container.level)
        )
        print(
            "  from:        "
            + format(old_location.x, "02.5f")
            + " "
            + format(old_location.y, "02.5f")
        )
        print(
            "  to:          "
            + format(mover.geometry.x, "02.5f")
            + " "
            + format(mover.geometry.y, "02.5f")
        )


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
    on the type. The supported types are "move", "single_run", "sequential", "conditional", and "delayed".
    For a "move" type activity, the dictionary should also contain a "mover", "destination" and can optionally contain
    a "moverProperties" dictionary containing an "engineOrder".
    For a "single_run" type activity, the dictionary should also contain an "origin", "destination", "loader", "mover",
    "unloader" and can optionally contain a "moverProperties" dictionary containing an "engineOrder" and/or "load".
    For a "sequential" type activity, the dictionary should also contain "activities". This is a list off activities
    (dictionaries as before) which will be performed until sequentially in the order in which they appear in the list.
    For a "conditional" type activity, the dictionary should also contain a "condition" and "activities", where the
    "activities" is another list of activities which will be performed until the event corresponding with the condition
    occurs.
    For a "delayed" type activity, the dictionary should also contain a "condition" and "activities", where the
    "activities" is another list of activities which will be performed after the event corresponding with the condition
    occurs.

    The "condition" of a "conditional" or "delayed" type activity is a dictionary containing an "operator" and one other
    field depending on the type. The operator can be "is_full", "is_empty", "is_done", "any_of" and "all_of".
    For the "is_full" operator, the dictionary should contain an "operand" which must be the id of the object (site or
    equipment) of which the container should be full for the event to occur.
    For the "is_empty" operator, the dictionary should contain an "operand" which must be the id of the object (site or
    equipment) of which the container should be empty for the event to occur.
    For the "is_done" operator, the dictionary should contain an "operand" which must the the id of an activity which
    should be finished for the event to occur. To instantiate such an event, the operand activity must already be
    instantiated. The Simulation class takes care of instantiating its activities in an order which ensures this is the
    case. However, if there is no such order because activities contain "is_done" conditions which circularly reference
    each other, a ValueError will be raised.
    For the "any_of" operator, the dictionary should contain "conditions", a list of (sub)conditions of which any must
    occur for the event to occur.
    For the "all_of" operator, the dictionary should contain "conditions", a list of (sub)conditions which all must
    occur for the event to occur.
    """

    def __init__(self, sites, equipment, activities, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__init_sites(sites)
        self.__init_equipment(equipment)
        self.__init_activities(activities)

    def __init_sites(self, sites):
        self.sites = {}
        for site in sites:
            self.sites[site["id"]] = self.__init_object_from_json(site)

    def __init_equipment(self, equipment):
        self.equipment = {}
        for equipment_piece in equipment:
            self.equipment[equipment_piece["id"]] = self.__init_object_from_json(
                equipment_piece
            )

    def __init_activities(self, activities):
        self.activities = {}
        activity_log_class = type("ActivityLog", (core.Log, core.Identifiable), {})
        uninstantiated_activities = activities
        while len(uninstantiated_activities) > 0:
            still_uninstantiated = self.__try_to_init_activities(
                activities, activity_log_class
            )
            if len(still_uninstantiated) == len(uninstantiated_activities):
                raise ValueError(
                    "Unable to instantiate activities {}; their is_done conditions form a circle.".format(
                        ", ".join(
                            activity["id"] for activity in uninstantiated_activities
                        )
                    )
                )
            uninstantiated_activities = still_uninstantiated

    def __try_to_init_activities(self, activities, activity_log_class):
        failed_activities = []
        for activity in activities:
            successful = self.__try_to_init_activity(activity, activity_log_class)
            if not successful:
                failed_activities.append(activity)
        return failed_activities

    def __try_to_init_activity(self, activity, activity_log_class):
        try:
            process_control = self.get_process_control(activity)
        except KeyError:
            return False

        id = activity["id"]
        activity_log = activity_log_class(env=self.env, name=id)

        process = self.env.process(
            process_control(activity_log=activity_log, env=self.env)
        )

        self.activities[id] = {"activity_log": activity_log, "process": process}
        return True

    def get_process_control(self, activity, stop_reservation_waiting_event=None):
        activity_type = activity["type"]

        if activity_type == "move":
            mover = self.equipment[activity["mover"]]
            mover_properties = self.get_mover_properties_kwargs(activity)
            destination = self.sites[activity["destination"]]
            kwargs = {"mover": mover, "destination": destination}
            if "engine_order" in mover_properties:
                kwargs["engine_order"] = mover_properties["engine_order"]
            return partial(move_process, **kwargs)
        if activity_type == "single_run":
            kwargs = self.get_mover_properties_kwargs(activity)
            kwargs["mover"] = self.equipment[activity["mover"]]
            kwargs["origin"] = self.sites[activity["origin"]]
            kwargs["destination"] = self.sites[activity["destination"]]
            kwargs["loader"] = self.equipment[activity["loader"]]
            kwargs["unloader"] = self.equipment[activity["unloader"]]
            if stop_reservation_waiting_event is not None:
                kwargs[
                    "stop_reservation_waiting_event"
                ] = stop_reservation_waiting_event
            return partial(single_run_process, **kwargs)
        if activity_type == "conditional":
            stop_event = self.get_condition_event(activity["condition"])
            sub_processes = [
                self.get_process_control(act, stop_reservation_waiting_event=stop_event)
                for act in activity["activities"]
            ]
            return partial(
                conditional_process, stop_event=stop_event, sub_processes=sub_processes
            )
        if activity_type == "sequential":
            sub_processes = [
                self.get_process_control(act) for act in activity["activities"]
            ]
            return partial(sequential_process, sub_processes=sub_processes)
        if activity_type == "delayed":
            sub_processes = [
                self.get_process_control(act) for act in activity["activities"]
            ]
            start_event = self.get_condition_event(activity["condition"])
            return partial(
                delayed_process, start_event=start_event, sub_processes=sub_processes
            )

        raise ValueError("Unrecognized activity type: " + activity_type)

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

    def get_level_event_operand(self, condition):
        operand_key = condition["operand"]
        try:
            operand = (
                self.sites[operand_key]
                if operand_key in self.sites
                else self.equipment[operand_key]
            )
        except KeyError:
            # rethrow a KeyError as a ValueError to avoid assuming there is a circular dependency
            raise ValueError(
                'No object with id "{}" present in configuration'.format(operand_key)
            )

        return operand

    def get_sub_condition_events(self, condition):
        conditions = condition["conditions"]
        events = [self.get_condition_event(condition) for condition in conditions]
        return events

    def get_condition_event(self, condition):
        operator = condition["operator"]

        if operator == "is_full":
            operand = self.get_level_event_operand(condition)
            return operand.container.get_full_event
        elif operator == "is_empty":
            operand = self.get_level_event_operand(condition)
            return operand.container.get_empty_event
        elif operator == "is_done":
            operand_key = condition["operand"]
            return self.activities[operand_key][
                "process"
            ]  # potential KeyError is caught in try_to_init_activity
        elif operator == "any_of":
            sub_events = self.get_sub_condition_events(condition)
            return self.env.any_of(events=sub_events)
        elif operator == "all_of":
            sub_events = self.get_sub_condition_events(condition)
            return self.env.all_of(events=sub_events)
        else:
            raise ValueError("Unrecognized operator type: " + operator)

    def __init_object_from_json(self, object_json):
        class_name = object_json["id"]
        name = object_json["name"]
        type = object_json["type"]
        properties = object_json["properties"]

        klass = get_class_from_type_list(class_name, type)
        kwargs = get_kwargs_from_properties(self.env, name, properties, self.sites)

        try:
            new_object = klass(**kwargs)
        except TypeError as type_err:
            # create a useful error message
            message_template = "Unable to instantiate {} for {}: {} with arguments {}"
            message = message_template.format(klass, class_name, type_err, kwargs)
            raise ValueError(message)

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
                self.get_as_feature_collection(
                    key, activity["activity_log"].get_log_as_json()
                )
            )
        json["activities"] = activity_logging

        return json

    @staticmethod
    def get_as_feature_collection(id, features):
        return dict(type="FeatureCollection", id=id, features=features)


def get_class_from_type_list(class_name, type_list):
    mixin_classes = (
        [core.Identifiable, core.Log]
        + [string_to_class(text) for text in type_list]
        + [core.DebugArgs]
    )
    return type(class_name, tuple(mixin_classes), {})


def string_to_class(text):
    try:
        return getattr(core, text)
    except AttributeError:
        raise ValueError("Invalid core class name given: " + text)


def get_kwargs_from_properties(environment, name, properties, sites):
    kwargs = {"env": environment, "name": name}

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

    # HasCosts
    if "dayrate" in properties:
        kwargs["dayrate"] = properties["dayrate"]
    elif "weekrate" in properties:
        kwargs["weekrate"] = properties["weekrate"]

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
        condition_objects = [
            core.SpillCondition(
                **get_spill_condition_kwargs(environment, condition_dict)
            )
            for condition_dict in condition_list
        ]
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
        kwargs["compute_draught"] = scipy.interpolate.interp1d(
            df["filling_degree"], df["draught"]
        )
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
            compute_function = scipy.interpolate.interp1d(
                df["filling_degree"], df["speed"]
            )
            kwargs["compute_v"] = compute_function
            v_empty = compute_function(0)
            v_full = compute_function(1)
        else:
            kwargs["v"] = speed
            v_empty = speed
            v_full = speed
    else:
        # set v_empty and v_full to dummy values to ensure we can instantiate energyUseSailing
        v_empty = 1.0
        v_full = 1.0

    # EnergyUse
    if "energyUseSailing" in properties:
        energy_use_sailing_dict = properties["energyUseSailing"]
        max_propulsion = energy_use_sailing_dict["maxPropulsion"]
        boardnet = energy_use_sailing_dict["boardnet"]
        kwargs["energy_use_sailing"] = partial(
            energy_use_sailing,
            speed_max_full=v_full,
            speed_max_empty=v_empty,
            propulsion_power_max=max_propulsion,
            boardnet_power=boardnet,
        )

    # EnergyUse
    if "energyUseLoading" in properties:
        kwargs["energy_use_loading"] = partial(
            energy_use_processing, constant_hourly_use=properties["energyUseLoading"]
        )
    if "energyUseUnloading" in properties:
        kwargs["energy_use_unloading"] = partial(
            energy_use_processing, constant_hourly_use=properties["energyUseUnloading"]
        )

    # HasResource
    if "nr_resources" in properties:
        kwargs["nr_resources"] = properties["nr_resources"]

    # Processor
    if "loadingRate" in properties:
        kwargs["loading_rate"] = get_loading_func(properties["loadingRate"])
    if "unloadingRate" in properties:
        kwargs["unloading_rate"] = get_unloading_func(properties["unloadingRate"])

    return kwargs


def add_object_properties(new_object, properties):
    # HasSoil
    if "layers" in properties:
        layer_list = properties["layers"]
        layer_objects = [
            core.SoilLayer(i, **layer_dict) for i, layer_dict in enumerate(layer_list)
        ]
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
        return lambda current_level, desired_level: scipy.integrate.quad(
            inversed_rate_function, current_level, desired_level
        )[0]
    else:
        # given property is a flat rate
        return property


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
        return lambda current_level, desired_level: scipy.integrate.quad(
            inversed_rate_function, desired_level, current_level
        )[0]
    else:
        # given property is a flat rate
        return property


def energy_use_sailing(
    distance,
    current_speed,
    filling_degree,
    speed_max_full,
    speed_max_empty,
    propulsion_power_max,
    boardnet_power,
):
    duration_seconds = distance / current_speed
    duration_hours = duration_seconds / 3600
    speed_factor_full = current_speed / speed_max_full
    speed_factor_empty = current_speed / speed_max_empty
    energy_use_sailing_full = duration_hours * (
        speed_factor_full ** 3 * propulsion_power_max + boardnet_power * 0.6
    )
    energy_use_sailing_empty = duration_hours * (
        speed_factor_empty ** 3 * propulsion_power_max + boardnet_power * 0.6
    )
    return (
        filling_degree * (energy_use_sailing_full - energy_use_sailing_empty)
        + energy_use_sailing_empty
    )


def energy_use_processing(duration_seconds, constant_hourly_use):
    duration_hours = duration_seconds / 3600
    return duration_hours * constant_hourly_use
