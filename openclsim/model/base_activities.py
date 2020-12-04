"""Base classes for the openclsim activities."""

from abc import ABC
from functools import partial

import simpy

import openclsim.core as core


class AbstractPluginClass(ABC):
    """
    Abstract class used as the basis for all Classes implementing a plugin for a specific Activity.

    Instance checks will be performed on this class level.
    """

    def __init__(self):
        pass

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        return {}

    def post_process(
        self,
        env,
        activity_log,
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
    """
    Base class for all activities which will provide a plugin mechanism.

    The plugin mechanism foresees that the plugin function pre_process is called before the activity is executed, while
    the function post_process is called after the activity has been executed.
    """

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
            yield from item["plugin"].post_process(*args, **kwargs)

    def delay_processing(self, env, activity_label, activity_log, waiting):
        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_START,
            activity_label=activity_label,
        )
        yield env.timeout(waiting)
        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_STOP,
            activity_label=activity_label,
        )


class GenericActivity(PluginActivity):
    """
    The GenericActivity Class forms a generic class which sets up all required mechanisms to control an activity by providing a start event.

    Since it is generic, a parameter of the initialization
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
        self.registry = registry
        self.postpone_start = postpone_start
        self.start_event = start_event
        self.requested_resources = requested_resources
        self.keep_resources = keep_resources
        self.done_event = self.env.event()

    def register_process(self, main_proc, show=False, additional_logs=None):
        # replace the done event
        self.done_event = self.env.event()

        # default to []
        if additional_logs is None:
            additional_logs = []

        start_event = None
        if self.start_event is not None:
            start_event = self.parse_expression(self.start_event)
        start_event_instance = start_event
        (
            start_event
            if start_event is None or isinstance(start_event, simpy.Event)
            else self.env.all_of(events=start_event)
        )

        print(self.id, start_event_instance)
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

        if "name" not in self.registry:
            self.registry["name"] = {}
        if self.name not in self.registry["name"]:
            l_ = []
        else:
            l_ = self.registry["name"][self.name]
        l_.append(self)
        self.registry["name"][self.name] = l_
        if "id" not in self.registry:
            self.registry["id"] = {}
        if self.id not in self.registry["id"]:
            l_ = []
        else:
            l_ = self.registry["id"][self.id]
        l_.append(self)
        self.registry["id"][self.id] = l_

    def parse_expression(self, expr):
        """Methods for Parsing of the expression language used for start_events and conditional_events."""
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
                        if state == "full":
                            if id_ is not None:
                                res.append(obj.container.get_full_event(id_=id_))
                            else:
                                res.append(obj.container.get_full_event())
                        elif state == "empty":
                            if id_ is not None:
                                res.append(obj.container.get_empty_event(id_=id_))
                            else:
                                res.append(obj.container.get_empty_event())
                        else:
                            raise Exception(
                                f"Unknown state {state} for a container event"
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
                        if activity_ is None:
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
            elif isinstance(key_val, simpy.Event):
                res.append(key_val)

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
        """
        Return a generator which can be added as a process to a simpy environment.

        In the process the given
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
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_START,
        )
        if isinstance(additional_logs, list) and len(additional_logs) > 0:
            for log in additional_logs:
                for sub_process in sub_processes:
                    log.log_entry(
                        t=env.now,
                        activity_id=activity_log.id,
                        activity_state=core.LogState.WAIT_START,
                    )
        yield start_event
        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_STOP,
        )
        if isinstance(additional_logs, list) and len(additional_logs) > 0:
            for log in additional_logs:
                for sub_process in sub_processes:
                    log.log_entry(
                        t=env.now,
                        activity_id=activity_log.id,
                        activity_state=core.LogState.WAIT_STOP,
                    )

        for sub_process in sub_processes:
            yield from sub_process(activity_log=activity_log, env=env)

    def _request_resource(self, requested_resources, resource):
        """Request the given resource and yields it."""
        if resource not in requested_resources:
            requested_resources[resource] = resource.request()
            yield requested_resources[resource]

    def _release_resource(self, requested_resources, resource, kept_resource=None):
        """
        Release the given resource, provided it does not equal the kept_resource parameter.

        Deletes the released resource from the requested_resources dictionary.
        """
        if kept_resource is not None:
            if isinstance(kept_resource, list):
                if resource in [item.resource for item in kept_resource]:
                    return
            elif resource == kept_resource.resource or resource == kept_resource:
                return

        if resource in requested_resources.keys():
            resource.release(requested_resources[resource])
            del requested_resources[resource]
