"""Test package."""

import datetime

import simpy

import openclsim.model as model

from .test_utils import parse_log


def test_process_synchronization():
    """Test process synchronization."""
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

    basic_activity_data = {
        "env": my_env,
        "name": "Activity1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
        "registry": registry,
        "additional_logs": [reporting_activity],
        "duration": 14,
    }
    model.BasicActivity(**basic_activity_data)
    basic_activity_data2 = {
        "env": my_env,
        "name": "Activity2",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
        "registry": registry,
        "additional_logs": [reporting_activity],
        "start_event": [{"type": "activity", "name": "Activity1", "state": "done"}],
        "duration": 30,
    }
    model.BasicActivity(**basic_activity_data2)

    my_env.run()

    benchmark = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 44),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
        ],
        "ActivityState": [
            "START",
            "START",
            "WAIT_START",
            "STOP",
            "STOP",
            "WAIT_STOP",
            "START",
            "STOP",
        ],
        "ObjectState": [{}, {}, {}, {}, {}, {}, {}, {}],
    }

    assert parse_log(reporting_activity.log) == benchmark
    assert my_env.now == 44
