"""Test package."""

import datetime

import simpy

import openclsim.model as model

from .test_utils import parse_log


class TestBasicActivity:
    """Test class for the basic activity."""

    def test_basic_activity(self):
        simulation_start = 0
        my_env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        basic_activity_data = {
            "env": my_env,
            "name": "Basic activity",
            "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
            "registry": registry,
            "duration": 14,
        }
        activity = model.BasicActivity(**basic_activity_data)
        my_env.run()
        benchmark_result = {
            "Message": ["Basic activity", "Basic activity"],
            "Timestamp": [
                datetime.datetime(1970, 1, 1, 0, 0),
                datetime.datetime(1970, 1, 1, 0, 0, 14),
            ],
            "Value": [14, 14],
            "Geometry": [None, None],
            "ActivityID": [
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            ],
            "ActivityState": ["START", "STOP"],
        }

        assert activity.log == benchmark_result

    def test_additional_logging(self):
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
            "name": "Basic activity",
            "registry": registry,
            "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
            "duration": 14,
            "additional_logs": [reporting_activity],
        }
        activity = model.BasicActivity(**basic_activity_data)
        my_env.run()

        benchmark_activity = {
            "Message": ["Basic activity", "Basic activity"],
            "Timestamp": [
                datetime.datetime(1970, 1, 1, 0, 0),
                datetime.datetime(1970, 1, 1, 0, 0, 14),
            ],
            "Value": [14, 14],
            "Geometry": [None, None],
            "ActivityID": [
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            ],
            "ActivityState": ["START", "STOP"],
        }
        benchmark_additional_log = {
            "Message": [
                "Reporting activity",
                "Basic activity",
                "Reporting activity",
                "Basic activity",
            ],
            "Timestamp": [
                datetime.datetime(1970, 1, 1, 0, 0),
                datetime.datetime(1970, 1, 1, 0, 0),
                datetime.datetime(1970, 1, 1, 0, 0),
                datetime.datetime(1970, 1, 1, 0, 0, 14),
            ],
            "Value": [0, 14, 0, 14],
            "Geometry": [None, None, None, None],
            "ActivityID": [
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
                "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            ],
            "ActivityState": ["START", "START", "STOP", "STOP"],
        }

        assert parse_log(reporting_activity.log) == benchmark_additional_log
        assert parse_log(activity.log) == benchmark_activity
