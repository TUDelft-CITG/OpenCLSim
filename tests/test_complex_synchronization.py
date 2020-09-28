"""Test package."""

import datetime

import simpy

import openclsim.model as model


def test_complex_synchronization():
    """Test complex synchronization."""
    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}
    keep_resources = {}

    reporting_activity_data = {
        "env": my_env,
        "name": "Reporting activity",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
        "registry": registry,
        "duration": 0,
        "postpone_start": False,
        "keep_resources": keep_resources,
    }
    reporting_activity = model.BasicActivity(**reporting_activity_data)

    sub_processes = []
    basic_activity_data1 = {
        "env": my_env,
        "name": "A Basic activity1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
        "registry": registry,
        "duration": 14,
        "postpone_start": True,
        "additional_logs": [reporting_activity],
        "keep_resources": keep_resources,
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data1))
    basic_activity_data2 = {
        "env": my_env,
        "name": "A Basic activity2",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
        "registry": registry,
        "duration": 10,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
        "keep_resources": keep_resources,
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data2))
    basic_activity_data3 = {
        "env": my_env,
        "name": "A Basic activity3",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
        "registry": registry,
        "duration": 220,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
        "keep_resources": keep_resources,
        "start_event": [
            {"type": "activity", "name": "B Basic activity2", "state": "done"}
        ],
    }
    sub_processes.append(model.BasicActivity(**basic_activity_data3))

    sequential_activity_data = {
        "env": my_env,
        "name": "A Sequential process",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
        "registry": registry,
        "sub_processes": sub_processes,
        "keep_resources": keep_resources,
    }
    activity = model.SequentialActivity(**sequential_activity_data)

    sub_processes2 = []
    basic_activity_data4 = {
        "env": my_env,
        "name": "B Basic activity1",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
        "registry": registry,
        "duration": 1,
        "postpone_start": True,
        "additional_logs": [reporting_activity],
        "keep_resources": keep_resources,
    }
    sub_processes2.append(model.BasicActivity(**basic_activity_data4))
    basic_activity_data5 = {
        "env": my_env,
        "name": "B Basic activity2",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
        "registry": registry,
        "duration": 500,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
        "keep_resources": keep_resources,
    }
    sub_processes2.append(model.BasicActivity(**basic_activity_data5))
    basic_activity_data6 = {
        "env": my_env,
        "name": "B Basic activity3",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
        "registry": registry,
        "duration": 120,
        "additional_logs": [reporting_activity],
        "postpone_start": True,
        "keep_resources": keep_resources,
    }
    sub_processes2.append(model.BasicActivity(**basic_activity_data6))

    sequential_activity_data2 = {
        "env": my_env,
        "name": "B Sequential process",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
        "registry": registry,
        "sub_processes": (proc for proc in sub_processes2),
        "keep_resources": keep_resources,
    }
    activity2 = model.SequentialActivity(**sequential_activity_data2)

    my_env.run()

    benchmark = {
        "Message": [
            "Reporting activity",
            "A Basic activity1",
            "B Basic activity1",
            "Reporting activity",
            "B Basic activity1",
            "B Basic activity2",
            "A Basic activity1",
            "A Basic activity2",
            "A Basic activity2",
            "A Basic activity3",
            "B Basic activity2",
            "A Basic activity3",
            "A Basic activity3",
            "B Basic activity3",
            "B Basic activity3",
            "A Basic activity3",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 1),
            datetime.datetime(1970, 1, 1, 0, 0, 1),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 14),
            datetime.datetime(1970, 1, 1, 0, 0, 24),
            datetime.datetime(1970, 1, 1, 0, 0, 24),
            datetime.datetime(1970, 1, 1, 0, 8, 21),
            datetime.datetime(1970, 1, 1, 0, 8, 21),
            datetime.datetime(1970, 1, 1, 0, 8, 21),
            datetime.datetime(1970, 1, 1, 0, 8, 21),
            datetime.datetime(1970, 1, 1, 0, 10, 21),
            datetime.datetime(1970, 1, 1, 0, 12, 1),
        ],
        "Value": [0, 14, 1, 0, 1, 500, 14, 10, 10, -1, 500, -1, 220, 120, 120, 220],
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
            None,
            None,
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5c",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "5dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
        ],
        "ActivityState": [
            "START",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "WAIT_START",
            "STOP",
            "WAIT_STOP",
            "START",
            "START",
            "STOP",
            "STOP",
        ],
    }
    assert reporting_activity.log == benchmark
