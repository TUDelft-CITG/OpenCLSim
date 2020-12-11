"""While activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity, StartSubProcesses


class ConditionProcessMixin:
    """Mixin for the condition process."""

    def conditional_process(self, activity_log, env):
        condition_event = self.parse_expression(self.condition_event)
        if (
            activity_log.log["Timestamp"]
            and activity_log.log["Timestamp"][-1] == "delayed activity started"
            and hasattr(condition_event, "__call__")
        ):
            condition_event = condition_event()

        if hasattr(condition_event, "__call__"):
            condition_event = condition_event()
        elif type(condition_event) == list:
            condition_event = env.any_of(events=[event() for event in condition_event])

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_while = env.now

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        repetitions = 1
        while True:
            self.start_sequence.succeed()
            for sub_process in self.sub_processes:
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

            if repetitions >= self.max_iterations or condition_event.processed is True:
                break
            else:
                repetitions += 1
                self.start_sequence = self.env.event()

                for sub_process in self.sub_processes:
                    sub_process.start()

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        yield from self.post_process(**args_data)

        yield env.timeout(0)


class WhileActivity(GenericActivity, ConditionProcessMixin, StartSubProcesses):
    """
    WhileActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.

    The while activity is a structural activity, which does not require specific resources.

    sub_processes
        the sub_processes which is executed in sequence in every iteration
    condition_event
        a condition event provided in the expression language which will stop the iteration as soon as the event is fulfilled.
    start_event
        the activity will start as soon as this event is triggered
        by default will be to start immediately
    """

    #     activity_log, env, stop_event, sub_processes, requested_resources, keep_resources
    def __init__(self, sub_processes, condition_event, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.print = show
        self.sub_processes = sub_processes

        self.condition_event = condition_event
        self.max_iterations = 1_000_000

        if not self.postpone_start:
            self.start()

    def start(self):
        self.start_sequential_subprocesses()
        self.register_process(main_proc=self.conditional_process)


class RepeatActivity(GenericActivity, ConditionProcessMixin, StartSubProcesses):
    """
    RepeatActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.

    Parameters
    ----------
    sub_processes
        the sub_processes which is executed in sequence in every iteration
    repetitions
        Number of times the subprocess is repeated
    start_event
        the activity will start as soon as this event is triggered
        by default will be to start immediately
    """

    def __init__(self, sub_processes, repetitions: int, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes

        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"In Sequence activity {self.name} the sub_process must have postpone_start=True"
                )

        self.max_iterations = repetitions
        self.condition_event = [
            {"type": "activity", "state": "done", "name": self.name}
        ]
        if not self.postpone_start:
            self.start()

    def start(self):
        self.start_sequential_subprocesses()
        self.register_process(main_proc=self.conditional_process)
