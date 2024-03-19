"""Parallel activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity, RegisterSubProcesses


class ParallelActivity(GenericActivity, RegisterSubProcesses):
    """
    ParallelActivity Class forms a specific class.

    This is for executing multiple activities in a dedicated order within a simulation.
    It is a structural activity, which does not require specific resources.

    Parameters
    ----------
    sub_processes
        a list of activities to be executed in Parallel.
    start_event
        The activity will start as soon as this event is processed
        by default will be to start immediately
    """

    def __init__(self, sub_processes, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes
        self.register_subprocesses = self.register_parallel_subprocesses
        self.register_subprocesses()

    def main_process_function(self, activity_log, env):
        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_time_parallel = env.now

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        self.start_parallel.succeed()

        stop_events = []
        subprocess_ids = []
        for sub_process in self.sub_processes:
            activity_log.log_entry_v1(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.START,
                activity_label={"type": "subprocess", "ref": sub_process.id},
            )

            stop_events.append(
                {"type": "activity", "state": "done", "name": sub_process.name}
            )
            subprocess_ids.append(sub_process.id)

        # wait until all stop events are processed
        while len(stop_events) > 0:
            # wait until any stop event is processed
            event_trigger = self.parse_expression(
                [{"or": [event for event in stop_events]}]
            )
            yield event_trigger
            # add a log line for each stop event and pop it
            i = 0
            while i < len(stop_events):
                if self.parse_expression(stop_events[i]).triggered is True:
                    stop_events.pop(i)
                    activity_log.log_entry_v1(
                        t=env.now,
                        activity_id=activity_log.id,
                        activity_state=core.LogState.STOP,
                        activity_label={
                            "type": "subprocess",
                            "ref": subprocess_ids.pop(i),
                        },
                    )
                else:
                    i += 1

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_time_parallel
        yield from self.post_process(**args_data)
