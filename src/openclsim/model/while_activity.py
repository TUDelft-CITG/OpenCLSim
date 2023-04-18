"""While activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity, RegisterSubProcesses
from .helpers import register_processes


class ConditionProcessMixin:
    """Mixin for the condition process."""

    def main_process_function(self, activity_log, env):
        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_while = env.now

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        static_condition_event = self.parse_expression(self.condition_event)
        repetitions = 1
        while True:
            self.start_sequence.succeed()
            for sub_process in self.sub_processes:
                activity_log.log_entry_v1(
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

                activity_log.log_entry_v1(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.STOP,
                    activity_label={
                        "type": "subprocess",
                        "ref": sub_process.id,
                    },
                )

            # We check both the static and reactive event. If a event is processed
            # and after that defused the event is overwritten and not longer reactive.
            # Since we cannot defuse simpy events we have to use this workaround.

            if (
                repetitions >= self.max_iterations
                or static_condition_event.processed is True
                or self.parse_expression(self.condition_event).processed is True
            ):
                break
            else:
                repetitions += 1

                # Reset the sequential start events of the subprocesses
                self.register_subprocesses()

                # Re-add the activities to the simpy environment
                register_processes(self.sub_processes)
        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        yield from self.post_process(**args_data)


class WhileActivity(GenericActivity, ConditionProcessMixin, RegisterSubProcesses):
    """
    Activity for executing multiple activities in a dedicated order within a simulation.

    The while activity is a structural activity, which does not require specific
    resources.

    sub_processes
        the sub_processes which is executed in sequence in every iteration
    condition_event
        a condition event provided in the expression language which will stop the
        iteration as soon as the event is fullfilled.
    start_event
        the activity will start as soon as this event is processed
        by default will be to start immediately
    """

    def __init__(self, sub_processes, condition_event, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.print = show
        self.sub_processes = sub_processes

        self.condition_event = condition_event
        self.max_iterations = 1_000_000

        self.register_subprocesses = self.register_sequential_subprocesses
        self.register_subprocesses()


class RepeatActivity(GenericActivity, ConditionProcessMixin, RegisterSubProcesses):
    """
    Activity for executing multiple activities in a dedicated order within a simulation.

    Parameters
    ----------
    sub_processes
        the sub_processes which is executed in sequence in every iteration
    repetitions
        Number of times the subprocess is repeated
    start_event
        the activity will start as soon as this event is processed
        by default will be to start immediately
    """

    def __init__(self, sub_processes, repetitions: int, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes
        self.max_iterations = repetitions
        self.condition_event = [
            {"type": "activity", "state": "done", "name": self.name}
        ]

        self.register_subprocesses = self.register_sequential_subprocesses
        self.register_subprocesses()
