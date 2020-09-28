"""Test package."""

import datetime

import simpy

import openclsim.model as model


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
        "sub_process": activity,
        "repetitions": 3,
        "postpone_start": False,
    }
    repeat_activity = model.RepeatActivity(**repeat_data)

    my_env.run()

    benchmark = {
        "Message": [
            "repeat process repeat",
            "sub process Basic activity",
            "Basic activity",
            "Basic activity",
            "sub process Basic activity",
            "sub process Basic activity",
            "Basic activity",
            "Basic activity",
            "sub process Basic activity",
            "sub process Basic activity",
            "Basic activity",
            "Basic activity",
            "sub process Basic activity",
            "repeat process repeat",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 28),
            datetime.datetime(1970, 1, 1, 0, 0, 28),
            datetime.datetime(1970, 1, 1, 0, 0, 28),
            datetime.datetime(1970, 1, 1, 0, 0, 28),
            datetime.datetime(1970, 1, 1, 0, 0, 42),
            datetime.datetime(1970, 1, 1, 0, 0, 42),
            datetime.datetime(1970, 1, 1, 0, 0, 42),
        ],
        "Value": [-1, -1, 14, 14, -1, -1, 14, 14, -1, -1, 14, 14, -1, -1],
        "Geometry": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        ],
        "ActivityState": [
            "START",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "STOP",
        ],
    }

    assert repeat_activity.log == benchmark
