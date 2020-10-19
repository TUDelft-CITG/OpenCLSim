"""Test package."""

import datetime

import simpy

import openclsim.model as model


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
    benchmark = {
        "Message": [
            "sequential Sequential process",
            "sub process Basic activity1",
            "sub process Basic activity1",
            "sub process Basic activity2",
            "sub process Basic activity2",
            "sub process Basic activity3",
            "sub process Basic activity3",
            "sequential Sequential process",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 19),
            datetime.datetime(1970, 1, 1, 0, 0, 19),
            datetime.datetime(1970, 1, 1, 0, 3, 59),
            datetime.datetime(1970, 1, 1, 0, 3, 59),
        ],
        "Value": [-1, -1, -1, -1, -1, -1, -1, -1],
        "Geometry": [None, None, None, None, None, None, None, None],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
        ],
        "ActivityState": [
            "START",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "STOP",
        ],
    }

    assert activity.log == benchmark
