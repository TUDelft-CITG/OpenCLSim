"""Sequential activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity


class SequentialActivity(GenericActivity):
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
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.sequential_process, show=self.print)

    def sequential_process(self, activity_log, env):
        """
        Return a generator which can be added as a process to a simpy.Environment.

        In the process the given
        sub_processes will be executed sequentially in the order in which they are given.

        activity_log: the core.Log object in which log_entries about the activities progress will be added.
        env: the simpy.Environment in which the process will be run
        sub_processes: an Iterable of methods which will be called with the activity_log and env parameters and should
                    return a generator which could be added as a process to a simpy.Environment
                    the sub_processes will be executed sequentially, in the order in which they are given
        """

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
        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"SequentialActivity requires all sub processes to have a postponed start. {sub_process.name} does not have attribute postpone_start."
                )
            activity_log.log_entry(
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.START,
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
                t=env.now,
                activity_id=activity_log.id,
                activity_state=core.LogState.STOP,
            )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_sequence
        yield from self.post_process(**args_data)

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )
