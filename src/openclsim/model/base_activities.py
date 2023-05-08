"""Base classes for the openclsim activities."""

from abc import ABC

import simpy

import openclsim.core as core


class AbstractPluginClass(ABC):
    """
    Abstract class used as the basis for all Classes implementing a
    plugin for a specific Activity.

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


class RegisterSubProcesses:
    """Mixin for the activities that want to execute their sub_processes in sequence."""

    def register_sequential_subprocesses(self):
        self.start_sequence = self.env.event()

        for i, sub_process in enumerate(self.sub_processes):
            if i == 0:
                sub_process.start_event_parent = self.start_sequence

            else:
                sub_process.start_event_parent = {
                    "type": "activity",
                    "state": "done",
                    "name": self.sub_processes[i - 1].name,
                }

        for sub_process in self.sub_processes:
            if hasattr(sub_process, "register_subprocesses"):
                sub_process.register_subprocesses()

    def register_parallel_subprocesses(self):
        self.start_parallel = self.env.event()

        for i, sub_process in enumerate(self.sub_processes):
            sub_process.start_event_parent = self.start_parallel

            if hasattr(sub_process, "register_subprocesses"):
                sub_process.register_subprocesses()


class PluginActivity(core.Identifiable, core.Log):
    """
    Base class for all activities which will provide a plugin mechanism.

    The plugin mechanism foresees that the plugin function pre_process is called before
    the activity is executed, while the function post_process is called after the
    activity has been executed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins = list()

    def register_plugin(self, plugin, priority=0):
        self.plugins.append({"priority": priority, "plugin": plugin})
        self.plugins = sorted(self.plugins, key=lambda x: x["priority"])

    def pre_process(self, args_data):
        # iterating over all registered plugins for this activity calling pre_process
        for item in self.plugins:
            yield from item["plugin"].pre_process(**args_data)

    def post_process(self, *args, **kwargs):
        # iterating over all registered plugins for this activity calling post_process
        for item in self.plugins:
            yield from item["plugin"].post_process(*args, **kwargs)

    def delay_processing(self, env, activity_label, activity_log, waiting):
        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_START,
            activity_label=activity_label,
        )
        yield env.timeout(waiting, value=activity_log.id)
        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.WAIT_STOP,
            activity_label=activity_label,
        )


class GenericActivity(PluginActivity):
    """The GenericActivity Class forms a generic class which sets up all activities."""

    def __init__(
        self,
        registry,
        start_event=None,
        requested_resources=None,
        keep_resources=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        requested_resources = (
            requested_resources if requested_resources is not None else {}
        )
        keep_resources = keep_resources if keep_resources is not None else []

        self.registry = registry
        self.start_event = start_event
        self.requested_resources = requested_resources
        self.keep_resources = keep_resources
        self.done_event = self.env.event()

    def register_process(self):
        # replace the events
        self.done_event = self.env.event()
        if hasattr(self, "start_sequence") and self.start_sequence.processed:
            self.start_sequence = self.env.event()
        if hasattr(self, "start_parallel") and self.start_parallel.processed:
            self.start_parallel = self.env.event()

        # Make container reservations
        if hasattr(self, "make_container_reservation"):
            self.make_container_reservation()

        # add the activity with start event to the simpy environment
        self.main_process = self.env.process(
            self.delayed_process(activity_log=self, env=self.env)
        )

        # add activity to the registry
        self.registry.setdefault("name", {}).setdefault(self.name, set()).add(self)
        self.registry.setdefault("id", {}).setdefault(self.id, set()).add(self)

    def parse_expression(self, expr):
        if isinstance(expr, simpy.Event):
            return expr
        if isinstance(expr, list):
            return self.env.all_of([self.parse_expression(item) for item in expr])
        if isinstance(expr, dict):
            if "and" in expr:
                return self.env.all_of(
                    [self.parse_expression(item) for item in expr["and"]]
                )
            if "or" in expr:
                return self.env.any_of(
                    [self.parse_expression(item) for item in expr["or"]]
                )
            if expr.get("type") == "container":
                id_ = expr.get("id_", "default")
                obj = expr["concept"]

                if (
                    expr.get("state") in ["gt", "ge", "lt", "le"]
                    and expr.get("level") is not None
                ):
                    return obj.container.get_container_event(
                        level=expr["level"],
                        operator=expr["state"],
                        id_=id_,
                    )
                elif expr["state"] == "full":
                    return obj.container.get_full_event(id_=id_)
                elif expr["state"] == "empty":
                    return obj.container.get_empty_event(id_=id_)
                raise ValueError

            if expr.get("type") == "activity":
                if expr.get("state") != "done":
                    raise ValueError(
                        f"Unknown state {expr.get('state')} in ActivityExpression."
                    )
                key = expr.get("ID", expr.get("name"))

                activity_ = None

                activity_from_id = self.registry.get("id", {}).get(key)
                activity_from_name = self.registry.get("name", {}).get(key)
                if activity_from_id is not None:
                    activity_ = activity_from_id
                elif activity_from_name is not None:
                    activity_ = activity_from_name
                else:
                    raise Exception(
                        f"No activity found in ActivityExpression for id/name {key} in expression {expr}\n"
                        f"registry by name:\n{self.registry.get('name')}\n"
                        f"registry by id:\n{self.registry.get('id')}\n"
                    )

                return self.env.all_of(
                    [activity_item.main_process for activity_item in activity_]
                )

            if expr.get("type") == "time":
                start = expr.get("start_time")
                return self.env.timeout(max(start - self.env.now, 0), value=self.id)
            raise ValueError

        raise ValueError(
            f"{type(expr)} is not a valid input type. Valid input types "
            "are: simpy.Event, dict, and list"
        )

    def delayed_process(
        self,
        activity_log,
        env,
    ):
        """Return a generator which can be added as a process to a simpy environment."""
        additional_logs = getattr(self, "additional_logs", [])
        start_event = (
            None
            if self.start_event is None
            else self.parse_expression(self.start_event)
        )

        if hasattr(self, "start_event_parent"):
            yield self.parse_expression(self.start_event_parent)

        start_time = env.now
        if start_event is not None:
            yield start_event

        if env.now > start_time:
            # log start
            activity_log.log_entry_v1(
                t=start_time,
                activity_id=activity_log.id,
                activity_state=core.LogState.WAIT_START,
            )
            for log in additional_logs:
                log.log_entry_v1(
                    t=start_time,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.WAIT_START,
                    activity_label={
                        "type": "additional log",
                        "ref": self.id,
                    },
                )

            # log stop
            activity_log.log_entry_v1(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.WAIT_STOP,
            )
            for log in additional_logs:
                log.log_entry_v1(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.WAIT_STOP,
                    activity_label={
                        "type": "additional log",
                        "ref": self.id,
                    },
                )

        yield from self.main_process_function(activity_log=self, env=self.env)

    def _request_resource(self, requested_resources, resource):
        """Request the given resource and yields it."""
        if resource not in requested_resources:
            requested_resources[resource] = resource.request()
            yield requested_resources[resource]

    def _release_resource(self, requested_resources, resource, kept_resource=None):
        """
        Release the given resource, if it does not equal the kept_resource parameter.

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
