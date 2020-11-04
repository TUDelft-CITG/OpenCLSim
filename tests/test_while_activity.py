"""Test package."""

import datetime

import simpy

import openclsim.model as model

from .test_utils import test_log


def test_while_activity():
    """Test the while activity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    basic_activity_data = {
        "env": my_env,
        "name": "Basic activity",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
        "registry": registry,
        "duration": 14,
        "postpone_start": True,
    }
    activity = model.BasicActivity(**basic_activity_data)

    while_data = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "while",  # We are moving soil
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
        "registry": registry,
        "sub_process": activity,
        "condition_event": [{"type": "activity", "name": "while", "state": "done"}],
        "postpone_start": False,
    }
    while_activity = model.WhileActivity(**while_data)

    my_env.run(until=50)

    assert my_env.now == 50
    test_log(while_activity.log)
