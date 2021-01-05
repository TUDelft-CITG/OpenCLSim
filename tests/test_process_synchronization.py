"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_process_synchronization():
    """Test process synchronization."""
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    reporting_activity = model.BasicActivity(
        env=my_env,
        name="Reporting activity",
        registry=registry,
        duration=0,
    )
    act1 = model.BasicActivity(
        env=my_env,
        name="Activity1",
        registry=registry,
        additional_logs=[reporting_activity],
        duration=14,
    )
    act2 = model.BasicActivity(
        env=my_env,
        name="Activity2",
        registry=registry,
        additional_logs=[reporting_activity],
        start_event=[{"type": "activity", "name": "Activity1", "state": "done"}],
        duration=30,
    )
    model.register_processes([reporting_activity, act1, act2])
    my_env.run()

    assert my_env.now == 44
    assert_log(act1)
    assert_log(act2)
    assert_log(reporting_activity)
