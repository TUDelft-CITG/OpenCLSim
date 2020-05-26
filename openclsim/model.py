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
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.origin = origin if type(origin) == list else [origin]
        self.destination = destination if type(destination) == list else [destination]

        self.start_event = (
            start_event
            if start_event is None or isinstance(start_event, simpy.Event)
            else self.env.all_of(events=start_event)
        )

        if type(stop_event) == list:
            stop_event = self.env.any_of(events=stop_event)

        if stop_event is not None:
            self.stop_event = stop_event

        elif start_event is None:
            stop_event = []
            stop_event.extend(orig.container.empty_event for orig in self.origin)
            stop_event.extend(dest.container.full_event for dest in self.destination)
            self.stop_event = self.env.any_of(stop_event)

        elif start_event:
            stop_event = []
            stop_event.extend(orig.container.get_empty_event for orig in self.origin)
            stop_event.extend(
                dest.container.get_full_event for dest in self.destination
            )
            self.stop_event = stop_event

        self.stop_reservation_waiting_event = (
            self.stop_event()
            if hasattr(self.stop_event, "__call__")
            else self.stop_event
        )

        self.loader = loader
        self.mover = mover
        self.unloader = unloader
        self.print = show

        single_run_proc = partial(
            single_run_process,
            origin=self.origin,
            destination=self.destination,
            loader=self.loader,
            mover=self.mover,
            unloader=self.unloader,
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


class GenericActivity(core.Identifiable, core.Log):
    """The GenericActivity Class forms a generic class which sets up all required mechanisms to control 
    an activity by providing start and end events. Since it is generic, a parameter of the initialization
    is the main process, which is provided by an inheriting class
    main_proc  : the main process to be executed
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        postpone_start=False,
        requested_resources=[],
        keep_resources=[],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.postpone_start = postpone_start
        self.requested_resources = requested_resources
        self.keep_resources = keep_resources

    def register_process(
        self, main_proc, start_event=None, stop_event=None, show=False,
    ):
        self.start_event = start_event
        (
            start_event
            if start_event is None or isinstance(start_event, simpy.Event)
            else self.env.all_of(events=start_event)
        )

        if type(stop_event) == list:
            stop_event = self.env.any_of(events=stop_event)

        if stop_event is not None:
            self.stop_event = self.env.any_of(stop_event)
        else:
            stop_event = []
            self.stop_event = self.env.any_of(stop_event)

        self.stop_reservation_waiting_event = (
            self.stop_event()
            if hasattr(self.stop_event, "__call__")
            else self.stop_event
        )

        # main_proc = partial(
        #    conditional_process,
        #    stop_event=self.stop_event,
        #    sub_processes=[main_proc],
        # )
        if start_event is not None:
            main_proc = partial(
                delayed_process, start_event=self.start_event, sub_processes=[main_proc]
            )
        self.main_proc = main_proc
        if not self.postpone_start:
            self.main_process = self.env.process(
                self.main_proc(activity_log=self, env=self.env)
            )


class MoveActivity(GenericActivity):
    """The MoveActivity Class forms a specific class for a single move activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        mover,
        destination,
        postpone_start=False,
        start_event=None,
        stop_event=None,
        show=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.destination = destination

        self.mover = mover
        # self.postpone_start = postpone_start
        self.print = show

        main_proc = partial(
            move_process,
            destination=self.destination,
            mover=self.mover,
            # stop_reservation_waiting_event=self.stop_reservation_waiting_event,
            # verbose=self.print,
        )
        self.register_process(
            main_proc=main_proc,
            start_event=start_event,
            stop_event=stop_event,
            show=show,
            # postpone_start=self.postpone_start,
        )


class BasicActivity(GenericActivity):
    """The MoveActivity Class forms a specific class for a single move activity within a simulation.
    It deals with a single origin container, destination container and a single combination of equipment
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        duration,
        # postpone_start=False,
        start_event=None,
        stop_event=None,
        show=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.duration = duration
        # self.postpone_start = postpone_start

        main_proc = partial(basic_process, duration=self.duration,)
        self.register_process(
            main_proc=main_proc,
            start_event=start_event,
            stop_event=stop_event,
            show=show,
            # postpone_start=self.postpone_start,
        )


class SequentialActivity(GenericActivity):
    """The SequenceActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.
    
    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        sub_processes,
        # postpone_start=False,
        start_event=None,
        stop_event=None,
        show=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes
        # self.postpone_start = postpone_start
        print(self.postpone_start)

        main_proc = partial(sequential_process, sub_processes=self.sub_processes,)
        self.register_process(
            main_proc=main_proc,
            start_event=start_event,
            stop_event=stop_event,
            show=show,
            # postpone_start=self.postpone_start,
        )


class ShiftAmountActivity(GenericActivity):
    """The ShiftAmountActivity Class forms a specific class for shifting material from an origin to a destination.
    It deals with a single origin container, destination container and a single processor
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class uses three different condition
    arguments: start_condition, stop_condition and condition. These condition arguments should all be given a condition
    object which has a satisfied method returning a boolean value. True if the condition is satisfied, False otherwise.

    destination: object inheriting from HasContainer, HasResource, Locatable, Identifiable and Log
    mover: moves to 'origin' if it is not already there, is loaded, then moves to 'destination' and is unloaded
           should inherit from Movable, HasContainer, HasResource, Identifiable and Log
           after the simulation is complete, its log will contain entries for each time it started moving,
           stopped moving, started loading / unloading and stopped loading / unloading
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    stop_event: the activity will stop (terminate) as soon as this event is triggered
                by default will be an event triggered when the destination container becomes full or the source
                container becomes empty
    """

    def __init__(
        self,
        processor,
        origin,
        destination,
        amount,
        id_="default",
        # postpone_start=False,
        start_event=None,
        stop_event=None,
        show=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.origin = origin
        self.destination = destination

        self.processor = processor
        self.amount = amount
        self.id_ = id_
        self.postpone_start = postpone_start
        self.print = show

        main_proc = partial(
            shift_amount_process,
            processor=self.processor,
            origin=self.origin,
            destination=self.destination,
            amount=self.amount,
            id_=self.id_,
            # stop_reservation_waiting_event=self.stop_reservation_waiting_event,
            # verbose=self.print,
        )
        self.register_process(
            main_proc=main_proc,
            start_event=start_event,
            stop_event=stop_event,
            show=show,
            # postpone_start=postpone_start,
        )


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
        "delayed activity", env.now, -1, None, activity_log.id, core.LogState.START
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
            print("conditional")
            yield from sub_process(activity_log=activity_log, env=env)

    activity_log.log_entry(
        "conditional processing", env.now, -1, None, activity_log.id, core.LogState.STOP
    )


def basic_process(activity_log, env, duration):
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

    activity_log.log_entry(
        activity_log.name, env.now, duration, None, activity_log.id, core.LogState.START
    )
    yield env.timeout(duration)
    activity_log.log_entry(
        activity_log.name, env.now, duration, None, activity_log.id, core.LogState.STOP
    )


def _request_resource_if_available(
    env,
    resource_requests,
    site,
    processor,
    amount,
    kept_resource,
    ActivityID,
    id_="default",
    engine_order=1.0,
    verbose=False,
):
    all_available = False
    while not all_available and amount > 0:
        # yield until enough content and space available in origin and destination
        yield env.all_of(
            events=[site.container.get_available(amount, id_),]
        )

        yield from _request_resource(resource_requests, processor.resource)
        print(f"processor request : {resource_requests}")
        if site.container.get_level(id_) < amount:
            # someone removed / added content while we were requesting the processor, so abort and wait for available
            # space/content again
            _release_resource(
                resource_requests, processor.resource, kept_resource=kept_resource
            )
            continue

        if not processor.is_at(site):
            # todo have the processor move simultaneously with the mover by starting a different process for it?
            yield from _move_mover(
                processor,
                site,
                ActivityID=ActivityID,
                engine_order=engine_order,
                verbose=verbose,
            )
            if site.container.get_level(id_) < amount:
                # someone messed us up again, so return to waiting for space/content
                _release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                continue

        yield from _request_resource(resource_requests, site.resource)
        print(f"site request : {resource_requests}")
        if site.container.get_level(id_) < amount:
            _release_resource(
                resource_requests, processor.resource, kept_resource=kept_resource
            )
            _release_resource(
                resource_requests, site.resource, kept_resource=kept_resource
            )
            continue
        all_available = True
        print(f"end requestIfAvailable : {resource_requests}")


def shift_amount_process(
    activity_log,
    env,
    processor,
    origin,
    destination,
    amount=None,
    id_="default",
    engine_order=1.0,
    stop_reservation_waiting_event=None,
):
    """Origin and Destination are of type HasContainer """
    print(origin)
    print(destination)
    print(processor)
    if not isinstance(origin, core.HasContainer) or not isinstance(
        destination, core.HasContainer
    ):
        raise Exception("Invalide use of method shift_amount")

    verbose = True
    filling = 1.0
    resource_requests = {}
    print(f"start : {resource_requests}")

    # Required for logging from json
    if not hasattr(activity_log, "processor"):
        activity_log.processor = processor
    if not hasattr(activity_log, "mover"):
        activity_log.mover = origin
    amount, all_amounts = processor.determine_processor_amount(
        [origin], destination, amount, id_
    )
    print(f"amount: {amount}   amounts:{all_amounts}")
    # Check if activity can start
    # If the transported amount is larger than zero, start activity
    print(f"amount {amount}")
    if 0 != amount:
        # vrachtbrief = mover.determine_schedule(amount, all_amounts, site, site)

        # origins = vrachtbrief[vrachtbrief["Type"] == "Origin"]
        # destinations = vrachtbrief[vrachtbrief["Type"] == "Destination"]
        yield from _request_resource(resource_requests, destination.resource)
        print(f"destination request : {resource_requests}")
        # for i in origins.index:
        #    origin = origins.loc[i, "ID"]
        #    amount = float(origins.loc[i, "Amount"])

        # print("_request_resources_if_transfer_possible")
        yield from _request_resource_if_available(
            env,
            resource_requests,
            origin,
            processor,
            amount,
            None,  # for now release all
            activity_log.id,
            id_,
            engine_order,
            verbose=False,
        )
        print(f"after req resource if available : {resource_requests}")
        activity_log.log_entry(
            activity_log.name,
            env.now,
            amount,
            None,
            activity_log.id,
            core.LogState.START,
        )
        # unload the mover
        print("_shift_amount")
        yield from _shift_amount(
            env,
            processor,
            origin,
            origin.container.get_level(id_) + amount,
            destination,
            ActivityID=activity_log.id,
            id_=id_,
            verbose=verbose,
        )
        activity_log.log_entry(
            activity_log.name,
            env.now,
            amount,
            None,
            activity_log.id,
            core.LogState.STOP,
        )
        print(f"after shift amount : {resource_requests}")

        # release the unloader, destination and mover requests
        # print("_release_resource")
        _release_resource(resource_requests, destination.resource)
        print(f"release destination : {resource_requests}")
        if origin.resource in resource_requests:
            _release_resource(resource_requests, origin.resource)
        print(f"released origin : {resource_requests}")
        # print("done")
    else:
        origin_requested = 0
        origin_left = 0
        destination_requested = 0

        for key in all_amounts.keys():
            if "origin" in key:
                origin_requested += all_amounts[key]
            else:
                destination_requested = all_amounts[key]

        if origin_requested == 0:
            events = [origin.container.reserve_get_available]
            activity_log.log_entry(
                "waiting origin reservation",
                env.now,
                origin.container.get_level(id_),
                origin.geometry,
                activity_log.id,
                core.LogState.START,
            )
            yield _or_optional_event(
                env, env.any_of(events), stop_reservation_waiting_event
            )
            activity_log.log_entry(
                "waiting origin reservation",
                env.now,
                origin.container.get_level(id_),
                origin.geometry,
                activity_log.id,
                core.LogState.STOP,
            )
        elif destination.container.get_level(id_) == destination.container.get_capacity(
            id_
        ):
            activity_log.log_entry(
                "waiting destination to finish",
                env.now,
                destination.container.get_capacity(id_),
                destination.geometry,
                activity_log.id,
                core.LogState.START,
            )
            yield env.timeout(3600)
            activity_log.log_entry(
                "waiting destination to finish",
                env.now,
                destination.container.get_capacity(id_),
                destination.geometry,
                activity_log.id,
                core.LogState.STOP,
            )

        else:
            raise RuntimeError("Attempting to move content with a full ship")
    # print(resource_requests)


def sequential_process(activity_log, env, sub_processes):
    """Returns a generator which can be added as a process to a simpy.Environment. In the process the given
    sub_processes will be executed sequentially in the order in which they are given.

    activity_log: the core.Log object in which log_entries about the activities progress will be added.
    env: the simpy.Environment in which the process will be run
    sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                   return a generator which could be added as a process to a simpy.Environment
                   the sub_processes will be executed sequentially, in the order in which they are given
    """
    activity_log.log_entry(
        "sequential", env.now, -1, None, activity_log.id, core.LogState.START
    )
    for sub_process in sub_processes:
        print(sub_process)
        print(sub_process.postpone_start)

        if not sub_process.postpone_start:
            # raise Exception(f"SequentialActivity requires all sub processes to have a postponed start. {sub_process.name} does not have attribute postpone_start.")
            print(
                (
                    f"SequentialActivity requires all sub processes to have a postponed start. {sub_process.name} does not have attribute postpone_start."
                )
            )
        activity_log.log_entry(
            f"sub process {sub_process.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.START,
        )
        yield from sub_process.main_proc(activity_log=sub_process, env=env)
        activity_log.log_entry(
            f"sub process {sub_process.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.STOP,
        )
    activity_log.log_entry(
        "sequential", env.now, -1, None, activity_log.id.core.LogState.STOP
    )


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
        "move activity of {} to {}".format(mover.name, destination.name),
        env.now,
        -1,
        mover.geometry,
        activity_log.id,
        core.LogState.START,
    )

    with mover.resource.request() as my_mover_turn:
        yield my_mover_turn

        mover.ActivityID = activity_log.id
        yield from mover.move(destination=destination, engine_order=engine_order)

    activity_log.log_entry(
        "move activity of {} to {}".format(mover.name, destination.name),
        env.now,
        -1,
        mover.geometry,
        activity_log.id,
        core.LogState.STOP,
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
    id_="default",
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

    amount, all_amounts = mover.determine_amount(
        origin, destination, loader, unloader, filling
    )

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
        vrachtbrief = mover.determine_schedule(amount, all_amounts, origin, destination)

        origins = vrachtbrief[vrachtbrief["Type"] == "Origin"]
        destinations = vrachtbrief[vrachtbrief["Type"] == "Destination"]

        if verbose:
            print("Using " + mover.name + " to process " + str(amount))
        activity_log.log_entry(
            "transporting",
            env.now,
            amount,
            mover.geometry,
            activity_log.id,
            core.LogState.START,
        )

        # request the mover's resource
        yield from _request_resource(resource_requests, mover.resource)

        for i in origins.index:
            origin = origins.loc[i, "ID"]
            amount = float(origins.loc[i, "Amount"])

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
                amount,
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
                mover.container.get_level() + amount,
                origin,
                ActivityID=activity_log.id,
                verbose=verbose,
            )

            # release the loader and origin resources (but always keep the mover requested)
            _release_resource(
                resource_requests, loader.resource, kept_resource=mover.resource
            )

            # If the loader is not the origin, release the origin as well
            if origin.resource in resource_requests.keys():
                _release_resource(
                    resource_requests, origin.resource, kept_resource=mover.resource
                )

        for i in destinations.index:
            destination = destinations.loc[i, "ID"]
            amount = float(destinations.loc[i, "Amount"])

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
                amount,
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
                mover.container.get_level(id_) - amount,
                destination,
                ActivityID=activity_log.id,
                verbose=verbose,
            )

            # release the unloader, destination and mover requests
            _release_resource(resource_requests, unloader.resource)
            if destination.resource in resource_requests:
                _release_resource(resource_requests, destination.resource)
            if mover.resource in resource_requests:
                _release_resource(resource_requests, mover.resource)

        activity_log.log_entry(
            "transporting",
            env.now,
            amount,
            mover.geometry,
            activity_log.id,
            core.LogState.STOP,
        )

    else:
        origin_requested = 0
        origin_left = 0
        destination_requested = 0
        destination_left = 0

        for key in all_amounts.keys():
            if "origin" in key:
                origin_requested += all_amounts[key]
            elif "destination" in key:
                destination_requested += all_amounts[key]

        if origin_requested == 0:
            events = [orig.container.reserve_get_available for orig in origin]
            activity_log.log_entry(
                "waiting origin reservation",
                env.now,
                mover.container.get_level(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.START,
            )
            yield _or_optional_event(
                env, env.any_of(events), stop_reservation_waiting_event
            )
            activity_log.log_entry(
                "waiting origin reservation",
                env.now,
                mover.container.get_level(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.STOP,
            )
        elif destination_requested == 0:
            events = [dest.container.reserve_put_available for dest in destination]
            activity_log.log_entry(
                "waiting destination reservation",
                env.now,
                mover.container.get_level(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.START,
            )
            yield _or_optional_event(
                env, env.any_of(events), stop_reservation_waiting_event
            )
            activity_log.log_entry(
                "waiting destination reservation",
                env.now,
                mover.container.get_level(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.STOP,
            )
        elif mover.container.get_level(id_) == mover.container.get_capacity(id_):
            activity_log.log_entry(
                "waiting mover to finish",
                env.now,
                mover.container.get_capacity(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.START,
            )
            yield env.timeout(3600)
            activity_log.log_entry(
                "waiting mover to finish",
                env.now,
                mover.container.get_capacity(id_),
                mover.geometry,
                activity_log.id,
                core.LogState.STOP,
            )

        else:
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


def _shift_amount(
    env,
    processor,
    origin,
    desired_level,
    destination,
    ActivityID,
    id_="default",
    verbose=False,
):
    print("start _shift_amount")
    """Calls the processor.process method, giving debug print statements when verbose is True."""
    amount = np.abs(origin.container.get_level(id_) - desired_level)
    print(f"amount {amount}")
    # Set ActivityID to processor and mover
    processor.ActivityID = ActivityID
    origin.ActivityID = ActivityID
    print("processor start process")
    # Check if loading or unloading
    yield from processor.process(origin, amount, destination, id_=id_, duration=10)
    print("processor end process")

    if verbose:
        org_level = origin.container.get_level(id_)
        dest_level = destination.container.get_level(id_)
        print(f"Processed {amount} of {id_}:")
        print(f"  by:          {processor.name}")
        print(f"  origin        {origin.name}  contains: {org_level} of {id_}")
        print(f"  destination:  {destination.name} contains: {dest_level} of {id_}")


def _request_resources_if_transfer_possible(
    env,
    resource_requests,
    origin,
    processor,
    destination,
    amount,
    kept_resource,
    ActivityID,
    id_="default",
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
                origin.container.get_available(amount, id_),
                destination.container.put_available(amount, id_),
            ]
        )

        yield from _request_resource(resource_requests, processor.resource)
        if (
            origin.container.get_level(id_) < amount
            or destination.container.get_capacity(id_)
            - destination.container.get_level(id_)
            < amount
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
                origin.container.get_level(id_) < amount
                or destination.container.get_capacity(id_)
                - destination.container.get_level(id_)
                < amount
            ):
                # someone messed us up again, so return to waiting for space/content
                _release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                continue

        yield from _request_resource(resource_requests, origin.resource)
        if (
            origin.container.get_level(id_) < amount
            or destination.container.get_capacity(id_)
            - destination.container.get_level(id_)
            < amount
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
            origin.container.get_level(id_) < amount
            or destination.container.get_capacity(id_)
            - destination.container.get_level(id_)
            < amount
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
            "  object:      "
            + mover.name
            + " contains: "
            + str(mover.container.get_level(id_))
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
