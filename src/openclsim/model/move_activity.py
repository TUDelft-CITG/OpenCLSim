"""Move activity for the simulation."""

import openclsim.core as core

from .base_activities import GenericActivity


class MoveActivity(GenericActivity):
    """
    MoveActivity Class forms a specific class for a single move activity

    It deals with a single origin container, destination container and a single
    combination of equipment to move substances from the origin to the destination.
    It will initiate and suspend processes according to a number of specified
    conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.

    To check when a transportation of substances can take place, the Activity class
    uses three different condition arguments: start_condition, stop_condition and
    condition. These condition arguments should all be given a condition object which
    has a satisfied method returning a boolean value. True if the condition is
    satisfied, False otherwise.

    Parameters
    ----------
    destination
        object inheriting from HasContainer, HasResource, Locatable,
        Identifiable and Log
    mover
        moves to 'origin' if it is not already there, is loaded, then moves
        to 'destination' and is unloaded should inherit from
        Movable, HasContainer, HasResource, Identifiable and Log
        after the simulation is complete, its log will contain entries
        for each time it started moving, stopped moving,
        started loading / unloading and stopped loading / unloading
    start_event
        the activity will start as soon as this event is processed
        by default will be to start immediately
    """

    def __init__(
        self,
        mover,
        destination,
        duration=None,
        show=False,
        engine_order=1,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.destination = destination
        self.mover = mover
        self.duration = duration
        self.print = show
        self.engine_order = engine_order

    def main_process_function(self, activity_log, env):
        """
        Return a generator which can be added as a process to a simpy.Environment.

        In the process, a move will be made
        by the mover, moving it to the destination.

        Parameters
        ----------
        activity_log
            the core.Log object in which log_entries about the activities
            progress will be added.
        env
            the simpy.Environment in which the process will be run
        mover
            moves from its current position to the destination
            should inherit from core.Movable
        destination
            the location the mover will move to
            should inherit from core.Locatable
        engine_order
            optional parameter specifying at what percentage of the maximum
            speed the mover should sail. for example, engine_order=0.5
            corresponds to sailing at 50% of max speed
        """

        yield from self._request_resource(self.requested_resources, self.mover.resource)

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        start_mover = env.now
        self.mover.activity_id = activity_log.id
        yield from self.mover.move(
            destination=self.destination,
            engine_order=self.engine_order,
            duration=self.duration,
        )

        activity_log.log_entry_v1(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_mover
        yield from self.post_process(**args_data)

        self._release_resource(
            self.requested_resources, self.mover.resource, self.keep_resources
        )
