"""Sequential activity for the simulation."""
import openclsim.core as core

from .base_activities import GenericActivity, StartSubProcesses


class SequentialActivity(GenericActivity, StartSubProcesses):
    """
    SequenceActivity Class forms a specific class.

    This is for executing multiple activities in a dedicated order within a simulation.
    It is a structural activity, which does not require specific resources.

    sub_processes:
        a list of activities to be executed in the provided sequence.
    start_event:
        The activity will start as soon as this event is triggered
        by default will be to start immediately
    """

    def __init__(self, sub_processes, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes

        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"In Sequence activity {self.name} the sub_process must have postpone_start=True"
                )

        self.start_sequential_subprocesses()

    def main_process_function(self, activity_log, env):
        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_sequence = env.now

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        self.start_sequence.succeed()

        for sub_process in self.sub_processes:

            sub_process_start_event = self.parse_expression(sub_process.start_event)
            if not sub_process_start_event.triggered:
                start_time = env.now
                yield sub_process_start_event
                if start_time < env.now:
                    sub_process.log_entry(
                        t=start_time,
                        activity_id=sub_process.id,
                        activity_state=core.LogState.WAIT_START,
                    )
                    sub_process.log_entry(
                        t=env.now,
                        activity_id=sub_process.id,
                        activity_state=core.LogState.WAIT_STOP,
                    )

            activity_log.log_entry(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.START,
                activity_label={
                    "type": "subprocess",
                    "ref": sub_process.id,
                },
            )

            stop_event = self.parse_expression(
                [
                    {
                        "type": "activity",
                        "state": "done",
                        "name": sub_process.name,
                    }
                ]
            )
            yield stop_event

            activity_log.log_entry(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.STOP,
                activity_label={
                    "type": "subprocess",
                    "ref": sub_process.id,
                },
            )

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_sequence
        yield from self.post_process(**args_data)
