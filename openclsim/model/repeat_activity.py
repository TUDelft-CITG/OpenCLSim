"""Repeat activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity


class RepeatActivity(GenericActivity):
    """
    RepeatActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.

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
        ii = 0
        while ii < self.repetitions:
            activity_log.log_entry(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.START,
                activity_label={
                    "type": "subprocess",
                    "ref": activity_log.id,
                },
            )
            self.sub_process.start()
            yield from self.sub_process.call_main_proc(
                activity_log=activity_log, env=env
            )
            self.sub_process.end()
            activity_log.log_entry(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.STOP,
                activity_label={
                    "type": "subprocess",
                    "ref": activity_log.id,
                },
            )
            # work around for the event evaluation
            # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
            # which will result in triggered but not processed events to be taken care of before further progressing
            # maybe there is a better way of doing it, but his option works for now.
            yield env.timeout(0)
            ii = ii + 1

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        yield from self.post_process(**args_data)

        yield env.timeout(0)