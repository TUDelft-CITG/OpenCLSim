"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_repeat_activity():
    """Test the repeat activity."""

    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    basic_activity_data = {
        "env": my_env,
        "name": "Basic activity",
        "registry": registry,
        "duration": 14,
        "postpone_start": True,
    }
    activity = model.BasicActivity(**basic_activity_data)

    repeat_data = {
        "env": my_env,
        "name": "repeat",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        "registry": registry,
        "sub_processes": [activity],
        "repetitions": 3,
        "postpone_start": False,
    }
    repeat_activity = model.RepeatActivity(**repeat_data)

    my_env.run()

    assert my_env.now == 42
    assert_log(repeat_activity.log)
