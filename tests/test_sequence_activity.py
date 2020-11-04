"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_sequence():
    """Test the sequence activity."""
    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    reporting_activity_data = {
        "env": my_env,
        "name": "Reporting activity",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
        "registry": registry,
        "duration": 0,
        "postpone_start": False,
    }
    reporting_activity = model.BasicActivity(**reporting_activity_data)

    sub_processes = []
    basic_activity_data1 = {
        "env": my_env,
        "name": "Basic activity1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
        "registry": registry,
        "duration": 14,
        "postpone_start": True,
        "additional_logs": [reporting_activity],
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data1))
    basic_activity_data2 = {
        "env": my_env,
        "name": "Basic activity2",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
        "registry": registry,
        "duration": 5,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data2))
    basic_activity_data3 = {
        "env": my_env,
        "name": "Basic activity3",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
        "registry": registry,
        "duration": 220,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data3))

    sequential_activity_data = {
        "env": my_env,
        "name": "Sequential process",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
        "registry": registry,
        "sub_processes": sub_processes,
    }
    activity = model.SequentialActivity(**sequential_activity_data)
    my_env.run()

    assert my_env.now == 239
    assert_log(activity.log)
