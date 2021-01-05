"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_parallel():
    """Test the parallel activity."""
    simulation_start = 0
    env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    reporting_activity = model.BasicActivity(
        env=env,
        name="Reporting activity",
        registry=registry,
        duration=0,
    )

    sub_processes = [
        model.BasicActivity(
            env=env,
            name="Basic activity1",
            registry=registry,
            duration=14,
            additional_logs=[reporting_activity],
        ),
        model.BasicActivity(
            env=env,
            name="Basic activity2",
            registry=registry,
            duration=5,
            additional_logs=[reporting_activity],
        ),
        model.BasicActivity(
            env=env,
            name="Basic activity3",
            registry=registry,
            duration=220,
            additional_logs=[reporting_activity],
        ),
    ]

    activity = model.ParallelActivity(
        env=env,
        name="Parallel process",
        registry=registry,
        sub_processes=sub_processes,
    )

    model.register_processes([activity])
    env.run()

    assert env.now == 220
    assert_log(activity)
    assert_log(reporting_activity)
