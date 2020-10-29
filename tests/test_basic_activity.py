"""Test package."""

import simpy

import openclsim.model as model


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
        model.BasicActivity(**basic_activity_data)
        my_env.run()

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
        model.BasicActivity(**basic_activity_data)
        my_env.run()
