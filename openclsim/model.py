from functools import partial
import openclsim.core as core
import simpy
import numpy as np

from abc import ABC


class AbstractPluginClass(ABC):
    """Abstract class used as the basis for all Classes implementing a plugin for a specific Activity. 
    Instance checks will be performed on this class level."""

    def __init__(self):
        pass

    def pre_process(self, env, activity_log, message, activity, *args, **kwargs):
        return {}

    def post_process(
        self,
        env,
        activity_log,
        message,
        activity,
        start_preprocessing,
        start_activity,
        *args,
        **kwargs,
    ):
        return {}

    def validate(self):
        pass


class PluginActivity(core.Identifiable, core.Log):
    """"This is the base class for all activities which will provide a plugin mechanism. 
    The plugin mechanism foresees that the plugin function pre_process is called before the activity is executed, while
    the function post_process is called after the activity has been executed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins = list()

    def get_priority(self, elem):
        return elem["priority"]

    def register_plugin(self, plugin, priority=0):
        self.plugins.append({"priority": priority, "plugin": plugin})
        self.plugins = sorted(self.plugins, key=self.get_priority)

    def pre_process(self, args_data):
        # iterating over all registered plugins for this activity calling pre_process
        for item in self.plugins:
            yield from item["plugin"].pre_process(**args_data)

    def post_process(self, *args, **kwargs):
        # iterating over all registered plugins for this activity calling post_process
        for item in self.plugins:
            item["plugin"].post_process(*args, **kwargs)

    def delay_processing(self, env, delay_name, activity_log, waiting):
        """Waiting must be a delay expressed in seconds"""
        activity_log.log_entry(
            delay_name, env.now, -1, None, activity_log.id, core.LogState.WAIT_START
        )
        yield env.timeout(waiting)
        activity_log.log_entry(
            delay_name, env.now, -1, None, activity_log.id, core.LogState.WAIT_STOP
        )


class GenericActivity(PluginActivity):
    """The GenericActivity Class forms a generic class which sets up all required mechanisms to control 
    an activity by providing a start event. Since it is generic, a parameter of the initialization
    is the main process, which is provided by an inheriting class
    main_proc  : the main process to be executed
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    requested_resources: a call by refernce value to a dictionary of resources, which have been requested and not released yet.
    keep_resources: a list of resources, which should not be released at the end of the activity
    postpone_start: if set to True, the activity will not be directly started in the simpy environment, 
                but will be started by a structrual activity, like sequential or while activity.
    """

    def __init__(
        self,
        registry,
        postpone_start=False,
        start_event=None,
        requested_resources=dict(),
        keep_resources=list(),
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        if "name" not in registry:
            registry["name"] = {}
        if self.name not in registry["name"]:
            l_ = []
        else:
            l_ = registry["name"][self.name]
        l_.append(self)
        registry["name"][self.name] = l_
        if "id" not in registry:
            registry["id"] = {}
        if self.id not in registry["id"]:
            l_ = []
        else:
            l_ = registry["id"][self.id]
        l_.append(self)
        registry["id"][self.id] = l_

        self.registry = registry
        self.postpone_start = postpone_start
        self.start_event = start_event
        self.requested_resources = requested_resources
        self.keep_resources = keep_resources
        self.done_event = self.env.event()

    def register_process(self, main_proc, show=False, additional_logs=[]):
        # replace the done event
        self.done_event = self.env.event()

        start_event = None
        if self.start_event != None:
            start_event = self.parse_expression(self.start_event)
        start_event_instance = start_event
        (
            start_event
            if start_event is None or isinstance(start_event, simpy.Event)
            else self.env.all_of(events=start_event)
        )
        if start_event_instance is not None:
            main_proc = partial(
                self.delayed_process,
                start_event=start_event_instance,
                sub_processes=[main_proc],
                additional_logs=additional_logs,
                requested_resources=self.requested_resources,
                keep_resources=self.keep_resources,
            )
        self.main_proc = main_proc
        if not self.postpone_start:
            self.main_process = self.env.process(
                self.main_proc(activity_log=self, env=self.env)
            )

    def parse_expression(self, expr):
        """Parsing of the expression language used for start_events and conditional_events."""
        res = []
        if not isinstance(expr, list):
            raise Exception(
                f"expression must be a list, but is {type(expr)}. Therefore it can not be parsed: {expr}"
            )
        for key_val in expr:
            if isinstance(key_val, dict):
                if "and" in key_val:
                    partial_res = self.parse_expression(key_val["and"])
                    self.env.timeout(0)
                    if not isinstance(partial_res, list):
                        partial_res = [partial_res]
                    res.append(
                        # self.env.all_of(events=[event() for event in partial_res])
                        self.env.all_of(events=partial_res)
                    )
                    self.env.timeout(0)
                elif "or" in key_val:
                    partial_res = self.parse_expression(key_val["or"])
                    self.env.timeout(0)
                    if not isinstance(partial_res, list):
                        partial_res = [partial_res]
                    res.append(
                        # self.env.any_of(events=[event() for event in partial_res])
                        self.env.any_of(events=partial_res)
                    )
                    self.env.timeout(0)
                elif "type" in key_val:
                    if key_val["type"] == "container":
                        id_ = None
                        if "id_" in key_val:
                            id_ = key_val["id_"]
                        state = key_val["state"]
                        obj = key_val["concept"]
                        if isinstance(obj, core.HasContainer):
                            if state == "full":
                                if id_ != None:
                                    res.append(obj.container.get_full_event(id_=id_))
                                else:
                                    res.append(obj.container.get_full_event())
                            elif state == "empty":
                                if id_ != None:
                                    res.append(obj.container.get_empty_event(id_=id_))
                                else:
                                    res.append(obj.container.get_empty_event())
                            else:
                                raise Exception(
                                    f"Unknown state {state} for a container event"
                                )
                        else:
                            raise Exception(
                                f"Referneced concept in a container expression is not of type HasContainer, but of type {type(obj)}"
                            )
                    elif key_val["type"] == "activity":
                        state = key_val["state"]
                        if state != "done":
                            raise Exception(
                                f"Unknown state {state} in ActivityExpression."
                            )
                        activity_ = None
                        key = "unknown"
                        if "ID" in key_val:
                            key = key_val["ID"]
                            if "id" in self.registry:
                                if key in self.registry["id"]:
                                    activity_ = self.registry["id"][key]
                        elif "name" in key_val:
                            key = key_val["name"]
                            if "name" in self.registry:
                                if key in self.registry["name"]:
                                    activity_ = self.registry["name"][key]
                        if activity_ == None:
                            raise Exception(
                                f"No activity found in ActivityExpression for id/name {key}"
                            )
                        if isinstance(activity_, list):
                            if len(activity_) == 1:
                                res.append(activity_[0].get_done_event())
                            else:
                                res.extend(
                                    [
                                        activity_item.get_done_event()
                                        for activity_item in activity_
                                    ]
                                )
                        else:
                            res.append(activity_[0].get_done_event())
                else:
                    raise Exception(
                        f"Logical AND can not have an additional key next to it. {expr}"
                    )
        if len(res) > 1:
            return res
        elif len(res) == 1:
            return res[0]
        return res

    def get_done_event(self):
        if self.postpone_start:
            return self.done_event
        elif hasattr(self, "main_process"):
            return self.main_process
        else:
            return self.done_event

    def call_main_proc(self, activity_log, env):
        res = self.main_proc(activity_log=activity_log, env=env)
        return res

    def end(self):
        self.done_event.succeed()

    def delayed_process(
        self,
        activity_log,
        env,
        start_event,
        sub_processes,
        requested_resources,
        keep_resources,
        additional_logs=[],
    ):
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
        activity_log.log_entry(
            activity_log.name,
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.WAIT_START,
        )
        if isinstance(additional_logs, list) and len(additional_logs) > 0:
            for log in additional_logs:
                for sub_process in sub_processes:
                    log.log_entry(
                        activity_log.name,
                        env.now,
                        -1,
                        None,
                        activity_log.id,
                        core.LogState.WAIT_START,
                    )
        yield start_event
        activity_log.log_entry(
            activity_log.name,
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.WAIT_STOP,
        )
        if isinstance(additional_logs, list) and len(additional_logs) > 0:
            for log in additional_logs:
                for sub_process in sub_processes:
                    log.log_entry(
                        activity_log.name,
                        env.now,
                        -1,
                        None,
                        activity_log.id,
                        core.LogState.WAIT_STOP,
                    )

        for sub_process in sub_processes:
            yield from sub_process(activity_log=activity_log, env=env)


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
    """

    def __init__(self, mover, destination, duration=None, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.destination = destination
        self.mover = mover
        self.duration = duration
        self.print = show
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.move_process, show=self.print)

    def move_process(self, activity_log, env):
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
        message = "move activity {} of {} to {}".format(
            self.name, self.mover.name, self.destination.name
        )
        yield from _request_resource(self.requested_resources, self.mover.resource)

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "message": message,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        activity_log.log_entry(
            message,
            env.now,
            -1,
            self.mover.geometry,
            activity_log.id,
            core.LogState.START,
        )

        start_mover = env.now
        self.mover.ActivityID = activity_log.id
        yield from self.mover.move(
            destination=self.destination,
            engine_order=1,
            duration=self.duration,
            activity_name=self.name,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_mover
        self.post_process(**args_data)

        _release_resource(
            self.requested_resources, self.mover.resource, self.keep_resources
        )

        # work around for the event evaluation
        # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
        # which will result in triggered but not processed events to be taken care of before further progressing
        # maybe there is a better way of doing it, but his option works for now.
        yield env.timeout(0)

        activity_log.log_entry(
            message,
            env.now,
            -1,
            self.mover.geometry,
            activity_log.id,
            core.LogState.STOP,
        )


class BasicActivity(GenericActivity):
    """The BasicActivity Class is a generic class to describe an activity, which does not require any specific resource, 
    but has a specific duration.

    duration: time required to perform the described activity.
    additional_logs: list of other concepts, where the start and the stop of the basic activity should be recorded.
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    def __init__(self, duration, additional_logs=[], show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.duration = duration
        self.additional_logs = additional_logs
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(
            main_proc=self.basic_process,
            show=self.print,
            additional_logs=self.additional_logs,
        )

    def basic_process(self, activity_log, env):
        """Returns a generator which can be added as a process to a simpy.Environment. The process will report the start of the 
        activity, delay the execution for the provided duration, and finally report the completion of the activiy.

        activity_log: the core.Log object in which log_entries about the activities progress will be added.
        env: the simpy.Environment in which the process will be run
        stop_event: a simpy.Event object, when this event occurs, the conditional process will finish executing its current
                    run of its sub_processes and then finish
        sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                    return a generator which could be added as a process to a simpy.Environment
                    the sub_processes will be executed sequentially, in the order in which they are given as long
                    as the stop_event has not occurred.
        """
        message = f"Basic activity {self.name}"

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "message": message,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_basic = env.now

        activity_log.log_entry(
            self.name,
            env.now,
            self.duration,
            None,
            activity_log.id,
            core.LogState.START,
        )

        if isinstance(self.additional_logs, list) and len(self.additional_logs) > 0:
            for log_item in self.additional_logs:
                log_item.log_entry(
                    self.name,
                    env.now,
                    self.duration,
                    None,
                    activity_log.id,
                    core.LogState.START,
                )

        yield env.timeout(self.duration)

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_basic
        self.post_process(**args_data)

        activity_log.log_entry(
            self.name, env.now, self.duration, None, activity_log.id, core.LogState.STOP
        )
        if isinstance(self.additional_logs, list) and len(self.additional_logs) > 0:
            for log_item in self.additional_logs:
                log_item.log_entry(
                    self.name,
                    env.now,
                    self.duration,
                    None,
                    activity_log.id,
                    core.LogState.STOP,
                )

        # work around for the event evaluation
        # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
        # which will result in triggered but not processed events to be taken care of before further progressing
        # maybe there is a better way of doing it, but his option works for now.
        yield env.timeout(0)


class SequentialActivity(GenericActivity):
    """The SequenceActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.
    It is a structural activity, which does not require specific resources.
    
    sub_processes: a list of activities to be executed in the provided sequence.
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    def __init__(self, sub_processes, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.sequential_process, show=self.print)

    def sequential_process(self, activity_log, env):
        """Returns a generator which can be added as a process to a simpy.Environment. In the process the given
        sub_processes will be executed sequentially in the order in which they are given.

        activity_log: the core.Log object in which log_entries about the activities progress will be added.
        env: the simpy.Environment in which the process will be run
        sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                    return a generator which could be added as a process to a simpy.Environment
                    the sub_processes will be executed sequentially, in the order in which they are given
        """
        message = f"Sequence activity {self.name}"

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "message": message,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_sequence = env.now

        activity_log.log_entry(
            f"sequential {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.START,
        )
        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"SequentialActivity requires all sub processes to have a postponed start. {sub_process.name} does not have attribute postpone_start."
                )
            activity_log.log_entry(
                f"sub process {sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.START,
            )
            sub_process.start()
            yield from sub_process.call_main_proc(activity_log=sub_process, env=env)
            sub_process.end()

            # work around for the event evaluation
            # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
            # which will result in triggered but not processed events to be taken care of before further progressing
            # maybe there is a better way of doing it, but his option works for now.
            yield env.timeout(0)
            activity_log.log_entry(
                f"sub process {sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.STOP,
            )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_sequence
        self.post_process(**args_data)

        activity_log.log_entry(
            f"sequential {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.STOP,
        )


class WhileActivity(GenericActivity):
    """The WhileActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.
    The while activity is a structural activity, which does not require specific resources.

    sub_process: the sub_process which is executed in every iteration
    condition_event: a condition event provided in the expression language which will stop the iteration as soon as the event is fulfilled.    
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    #     activity_log, env, stop_event, sub_processes, requested_resources, keep_resources
    def __init__(self, sub_process, condition_event, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.max_iterations = 1_000_000
        self.print = show
        self.sub_process = sub_process
        if not self.sub_process.postpone_start:
            raise Exception(
                f"In While activity {self.name} the sub_process must have postpone_start=True"
            )
        self.condition_event = condition_event

        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.conditional_process, show=self.print)

    def conditional_process(self, activity_log, env):
        """Returns a generator which can be added as a process to a simpy.Environment. In the process the given
        self.sub_process will be executed until the given condition_event occurs. If the condition_event occurs during the execution
        of the self.sub_process, the conditional process will first complete the self.sub_process before finishing its own process.

        activity_log: the core.Log object in which log_entries about the activities progress will be added.
        env: the simpy.Environment in which the process will be run
        condition_event: a simpy.Event object, when this event occurs, the conditional process will finish executing its current
                    run of its sub_processes and then finish
        self.sub_process: an Iterable of methods which will be called with the activity_log and env parameters and should
                    return a generator which could be added as a process to a simpy.Environment
                    the sub_processes will be executed sequentially, in the order in which they are given as long
                    as the stop_event has not occurred.
        """
        message = f"While activity {self.name}"
        condition_event = self.parse_expression(self.condition_event)

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "message": message,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_while = env.now

        if activity_log.log["Message"]:
            if activity_log.log["Message"][
                -1
            ] == "delayed activity started" and hasattr(condition_event, "__call__"):
                condition_event = condition_event()

        if hasattr(condition_event, "__call__"):
            condition_event = condition_event()
        elif type(condition_event) == list:
            condition_event = env.any_of(events=[event() for event in condition_event])

        activity_log.log_entry(
            f"conditional process {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.START,
        )
        ii = 0
        while (not condition_event.processed) and ii < self.max_iterations:
            # for sub_process_ in (proc for proc in [self.sub_process]):
            activity_log.log_entry(
                f"sub process {self.sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.START,
            )
            self.sub_process.start()
            yield from self.sub_process.call_main_proc(
                activity_log=activity_log, env=env
            )
            self.sub_process.end()
            activity_log.log_entry(
                f"sub process {self.sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.STOP,
            )
            # work around for the event evaluation
            # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
            # which will result in triggered but not processed events to be taken care of before further progressing
            # maybe there is a better way of doing it, but his option works for now.
            yield env.timeout(0)
            ii = ii + 1

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        self.post_process(**args_data)

        activity_log.log_entry(
            f"conditional process {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.STOP,
        )


class RepeatActivity(GenericActivity):
    """The RepeatActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.
    The while activity is a structural activity, which does not require specific resources.

    Parameters
    ----------

    sub_process
        the sub_process which is executed in every iteration
    repetitions
        Number of times the subprocess is repeated    
    start_event
        the activity will start as soon as this event is triggered
        by default will be to start immediately
    """

    def __init__(self, sub_process, repetitions: int, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_process = sub_process
        if not self.sub_process.postpone_start:
            raise Exception(
                f"In Repeat activity {self.name} the sub_process must have postpone_start=True"
            )
        self.repetitions = repetitions
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.repeat_process, show=self.print)

    def repeat_process(self, activity_log, env):
        message = f"Repeat activity {self.name}"

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "message": message,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_while = env.now

        activity_log.log_entry(
            f"repeat process {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.START,
        )
        ii = 0
        while ii < self.repetitions:
            activity_log.log_entry(
                f"sub process {self.sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.START,
            )
            self.sub_process.start()
            yield from self.sub_process.call_main_proc(
                activity_log=activity_log, env=env
            )
            self.sub_process.end()
            activity_log.log_entry(
                f"sub process {self.sub_process.name}",
                env.now,
                -1,
                None,
                activity_log.id,
                core.LogState.STOP,
            )
            # work around for the event evaluation
            # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
            # which will result in triggered but not processed events to be taken care of before further progressing
            # maybe there is a better way of doing it, but his option works for now.
            yield env.timeout(0)
            ii = ii + 1

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        self.post_process(**args_data)

        activity_log.log_entry(
            f"repeat process {self.name}",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.STOP,
        )


class ShiftAmountActivity(GenericActivity):
    """The ShiftAmountActivity Class forms a specific class for shifting material from an origin to a destination.
    It deals with a single origin container, destination container and a single processor
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    
    origin: container where the source objects are located.
    destination: container, where the objects are assigned to
    processor: resource responsible to implement the transfer.
    amount: the maximum amount of objects to be transfered.
    duration: time specified in seconds on how long it takes to transfer the objects.
    id_: in case of MultiContainers the id_ of the container, where the objects should be removed from or assiged to respectively.
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    def __init__(
        self,
        processor,
        origin,
        destination,
        duration=None,
        amount=None,
        id_="default",
        show=False,
        phase=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.origin = origin
        self.destination = destination

        self.processor = processor
        self.amount = amount
        self.duration = duration
        self.id_ = id_
        self.print = show
        self.phase = phase

        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.shift_amount_process, show=self.print)

    def _request_resource_if_available(
        self,
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
            yield env.all_of(events=[site.container.get_available(amount, id_)])

            yield from _request_resource(resource_requests, processor.resource)
            if site.container.get_level(id_) < amount:
                # someone removed / added content while we were requesting the processor, so abort and wait for available
                # space/content again
                _release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                continue

            if not processor.is_at(site):
                # todo have the processor move simultaneously with the mover by starting a different process for it?
                yield from self._move_mover(
                    processor,
                    site,
                    ActivityID=ActivityID,
                    engine_order=engine_order,
                    verbose=verbose,
                )
                if site.container.get_level(id_) < amount:
                    # someone messed us up again, so return to waiting for space/content
                    _release_resource(
                        resource_requests,
                        processor.resource,
                        kept_resource=kept_resource,
                    )
                    continue

            yield from _request_resource(resource_requests, site.resource)
            if site.container.get_level(id_) < amount:
                _release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                _release_resource(
                    resource_requests, site.resource, kept_resource=kept_resource
                )
                continue
            all_available = True

    def shift_amount_process(self, activity_log, env):
        """Origin and Destination are of type HasContainer """
        assert self.processor.is_at(self.origin)
        assert self.destination.is_at(self.origin)

        verbose = False
        filling = 1.0
        resource_requests = self.requested_resources

        if not hasattr(activity_log, "processor"):
            activity_log.processor = self.processor
        if not hasattr(activity_log, "mover"):
            activity_log.mover = self.origin
        self.amount, all_amounts = self.processor.determine_processor_amount(
            [self.origin], self.destination, self.amount, self.id_
        )

        if 0 != self.amount:

            yield from _request_resource(resource_requests, self.destination.resource)

            yield from self._request_resource_if_available(
                env,
                resource_requests,
                self.origin,
                self.processor,
                self.amount,
                None,  # for now release all
                activity_log.id,
                self.id_,
                1,
                verbose=False,
            )

            if self.duration is not None:
                rate = None
            elif self.duration is not None:
                rate = self.processor.loading

            elif self.phase == "loading":
                rate = self.processor.loading
            elif self.phase == "unloading":
                rate = self.processor.unloading
            else:
                raise RuntimeError(
                    f"Both the pase (loading / unloading) and the duration of the shiftamount activity are undefined. At least one is required!"
                )

            start_time = env.now
            args_data = {
                "env": env,
                "activity_log": activity_log,
                "message": self.name,
                "activity": self,
            }
            yield from self.pre_process(args_data)

            activity_log.log_entry(
                self.name,
                env.now,
                self.amount,
                None,
                activity_log.id,
                core.LogState.START,
            )

            start_shift = env.now
            yield from self._shift_amount(
                env,
                self.processor,
                self.origin,
                self.origin.container.get_level(self.id_) + self.amount,
                self.destination,
                activity_name=self.name,
                ActivityID=activity_log.id,
                duration=self.duration,
                rate=rate,
                id_=self.id_,
                verbose=verbose,
            )

            args_data["start_preprocessing"] = start_time
            args_data["start_activity"] = start_shift
            self.post_process(**args_data)

            activity_log.log_entry(
                self.name,
                env.now,
                self.amount,
                None,
                activity_log.id,
                core.LogState.STOP,
            )

            # release the unloader, self.destination and mover requests
            _release_resource(
                resource_requests, self.destination.resource, self.keep_resources
            )
            if self.origin.resource in resource_requests:
                _release_resource(
                    resource_requests, self.origin.resource, self.keep_resources
                )
            if self.processor.resource in resource_requests:
                _release_resource(
                    resource_requests, self.processor.resource, self.keep_resources
                )

            # work around for the event evaluation
            # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
            # which will result in triggered but not processed events to be taken care of before further progressing
            # maybe there is a better way of doing it, but his option works for now.
            yield env.timeout(0)
        else:
            raise RuntimeError(
                f"Attempting to shift content from an empty origin or to a full self.destination. ({all_amounts})"
            )

    def _move_mover(self, mover, origin, ActivityID, engine_order=1.0, verbose=False):
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
                + str(mover.container.get_level())
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

    def _shift_amount(
        self,
        env,
        processor,
        origin,
        desired_level,
        destination,
        ActivityID,
        activity_name,
        duration=None,
        rate=None,
        id_="default",
        verbose=False,
    ):
        """Calls the processor.process method, giving debug print statements when verbose is True."""
        amount = np.abs(origin.container.get_level(id_) - desired_level)
        # Set ActivityID to processor and mover
        processor.ActivityID = ActivityID
        origin.ActivityID = ActivityID

        # Check if loading or unloading

        yield from processor.process(
            origin,
            amount,
            destination,
            id_=id_,
            duration=duration,
            rate=rate,
            activity_name=activity_name,
        )

        if verbose:
            org_level = origin.container.get_level(id_)
            dest_level = destination.container.get_level(id_)
            print(f"Processed {amount} of {id_}:")
            print(f"  by:          {processor.name}")
            print(f"  origin        {origin.name}  contains: {org_level} of {id_}")
            print(f"  destination:  {destination.name} contains: {dest_level} of {id_}")


def _request_resource(requested_resources, resource):
    """Requests the given resource and yields it.
    """
    if resource not in requested_resources:
        requested_resources[resource] = resource.request()
        yield requested_resources[resource]


def _release_resource(requested_resources, resource, kept_resource=None):
    """Releases the given resource, provided it does not equal the kept_resource parameter.
    Deletes the released resource from the requested_resources dictionary."""
    if kept_resource != None:
        if isinstance(kept_resource, list):
            if resource in [item.resource for item in kept_resource]:
                return
        elif resource == kept_resource.resource or resource == kept_resource:
            return

    if resource in requested_resources.keys():
        resource.release(requested_resources[resource])
        del requested_resources[resource]


def single_run_process(
    env,
    registry,
    name,
    origin,
    destination,
    mover,
    loader,
    unloader,
    start_event=None,
    stop_event=[],
    requested_resources={},
    postpone_start=False,
):

    if stop_event == []:
        stop_event = [
            {
                "or": [
                    {"type": "container", "concept": origin, "state": "empty"},
                    {"type": "container", "concept": destination, "state": "full"},
                ]
            }
        ]

    single_run = [
        MoveActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            postpone_start=True,
            name=f"{name} sailing empty",
            mover=mover,
            destination=origin,
        ),
        ShiftAmountActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            postpone_start=True,
            phase="loading",
            name=f"{name} loading",
            processor=loader,
            origin=origin,
            destination=mover,
        ),
        MoveActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            postpone_start=True,
            name=f"{name} sailing filled",
            mover=mover,
            destination=destination,
        ),
        ShiftAmountActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            phase="unloading",
            name=f"{name} unloading",
            postpone_start=True,
            processor=unloader,
            origin=mover,
            destination=destination,
        ),
    ]

    activity = SequentialActivity(
        env=env,
        name=f"{name} sequence",
        registry=registry,
        sub_processes=single_run,
        postpone_start=True,
    )

    while_activity = WhileActivity(
        env=env,
        name=name,
        registry=registry,
        sub_process=activity,
        condition_event=stop_event,
        start_event=start_event,
        postpone_start=postpone_start,
    )

    return single_run, activity, while_activity
