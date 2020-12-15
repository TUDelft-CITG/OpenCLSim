"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_sequence():
    """Test the sequence activity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    reporting_activity_data = {
        "env": my_env,
        "name": "Reporting activity",
        "registry": registry,
        "duration": 0,
    }
    reporting_activity = model.BasicActivity(**reporting_activity_data)

    sub_processes = []
    basic_activity_data1 = {
        "env": my_env,
        "name": "Basic activity1",
        "registry": registry,
        "duration": 14,
        "additional_logs": [reporting_activity],
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data1))
    basic_activity_data2 = {
        "env": my_env,
        "name": "Basic activity2",
        "registry": registry,
        "duration": 5,
        "additional_logs": [reporting_activity],
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data2))
    basic_activity_data3 = {
        "env": my_env,
        "name": "Basic activity3",
        "registry": registry,
        "duration": 220,
        "additional_logs": [reporting_activity],
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data3))

    sequential_activity_data = {
        "env": my_env,
        "name": "Sequential process",
        "registry": registry,
        "sub_processes": sub_processes,
    }
    activity = model.SequentialActivity(**sequential_activity_data)
    my_env.run()

    assert my_env.now == 239
    assert_log(activity.log)
