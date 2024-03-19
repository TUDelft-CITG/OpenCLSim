"""Base classes for the openclsim activities."""

import openclsim.core as core

from .base_activities import GenericActivity


class BasicActivity(GenericActivity):
    """
    BasicActivity Class is a generic class to describe an activity, which does not
    require any specific resource, but has a specific duration.

    Parameters
    ----------
    duration
        time required to perform the described activity.
    name
        human readable name, to be displayed in logs and gannt charts.
    additional_logs
        list of other concepts, where the start and the stop of the basic
        activity should be recorded.
    start_event
        the activity will start as soon as this event is processed,
        by default will be to start immediately
    registry
        registry for logs
    """

    def __init__(self, duration, additional_logs=None, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.duration = duration
        if additional_logs is None:
            additional_logs = []
        self.additional_logs = additional_logs

    def main_process_function(self, activity_log, env):
        """
        Return a generator which can be added as a process to a simpy.Environment.

        The process will report the start of the activity, delay the execution for
        the provided duration, and finally report the completion of the activity.

        Parameters
        ----------
        activity_log
            the core.Log object in which log_entries about the
            activities progress will be added.
        env
            the simpy.Environment in which the process will be run
        stop_event
            a simpy.Event object, when this event occurs, the
            conditional process will finish executing its current
            run of its sub_processes and then finish
        sub_processes
            an Iterable of methods which will be called with the
            activity_log and env parameters and should return a
            generator which could be added as a process to a
            simpy.Environment the sub_processes will be executed
            sequentially, in the order in which they are given as
            long as the stop_event has not occurred.
        """

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_basic = env.now

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        if isinstance(self.additional_logs, list) and len(self.additional_logs) > 0:
            for log_item in self.additional_logs:
                log_item.log_entry_v1(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.START,
                    activity_label={
                        "type": "additional log",
                        "ref": self.id,
                    },
                )

        yield env.timeout(self.duration, value=activity_log.id)

        activity_log.log_entry_v1(
            t=env.now, activity_id=activity_log.id, activity_state=core.LogState.STOP
        )
        if isinstance(self.additional_logs, list) and len(self.additional_logs) > 0:
            for log_item in self.additional_logs:
                log_item.log_entry_v1(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.STOP,
                    activity_label={
                        "type": "additional log",
                        "ref": self.id,
                    },
                )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_basic
        yield from self.post_process(**args_data)
