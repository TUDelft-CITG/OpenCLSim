"""Single run activity for the simulation."""

from .move_activity import MoveActivity
from .shift_amount_activity import ShiftAmountActivity
from .while_activity import WhileActivity


def single_run_process(
    env,
    registry,
    name,
    origin,
    destination,
    mover,
    loader,
    unloader,
    start_event=None,
    stop_event=None,
    requested_resources=None,
):
    """Single run activity for the simulation."""

    if stop_event is None:
        stop_event = []

    if requested_resources is None:
        requested_resources = {}

    if stop_event == []:
        stop_event = [
            {
                "or": [
                    {"type": "container", "concept": origin, "state": "empty"},
                    {"type": "container", "concept": destination, "state": "full"},
                ]
            }
        ]

    single_run = [
        MoveActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            name=f"{name} sailing empty",
            mover=mover,
            destination=origin,
        ),
        ShiftAmountActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            phase="loading",
            name=f"{name} loading",
            processor=loader,
            origin=origin,
            destination=mover,
        ),
        MoveActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            name=f"{name} sailing filled",
            mover=mover,
            destination=destination,
        ),
        ShiftAmountActivity(
            env=env,
            registry=registry,
            requested_resources=requested_resources,
            phase="unloading",
            name=f"{name} unloading",
            processor=unloader,
            origin=mover,
            destination=destination,
        ),
    ]

    while_activity = WhileActivity(
        env=env,
        name=name,
        registry=registry,
        sub_processes=single_run,
        condition_event=stop_event,
        start_event=start_event,
    )

    return single_run, while_activity
