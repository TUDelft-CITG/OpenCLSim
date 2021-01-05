"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_sequence():
    """Test the sequence activity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    reporting_activity = model.BasicActivity(
        env=my_env,
        name="Reporting activity",
        registry=registry,
        duration=0,
    )

    sub_processes = [
        model.BasicActivity(
            env=my_env,
            name="Basic activity1",
            registry=registry,
            duration=14,
            additional_logs=[reporting_activity],
        ),
        model.BasicActivity(
            env=my_env,
            name="Basic activity2",
            registry=registry,
            duration=5,
            additional_logs=[reporting_activity],
        ),
        model.BasicActivity(
            env=my_env,
            name="Basic activity3",
            registry=registry,
            duration=220,
            additional_logs=[reporting_activity],
        ),
    ]

    activity = model.SequentialActivity(
        env=my_env,
        name="Sequential process",
        registry=registry,
        sub_processes=sub_processes,
    )
    model.register_processes([activity])
    my_env.run()

    assert my_env.now == 239
    assert_log(activity)
