"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


class TestBasicActivity:
    """Test class for the basic activity."""

    def test_basic_activity(self):
        simulation_start = 0
        my_env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        act = model.BasicActivity(
            env=my_env,
            name="Basic activity",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            registry=registry,
            duration=14,
        )
        model.register_processes([act])
        my_env.run()

        assert my_env.now == 14

    def test_additional_logging(self):
        simulation_start = 0
        my_env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        reporting_activity = model.BasicActivity(
            env=my_env,
            name="Reporting activity",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5k",
            registry=registry,
            duration=0,
        )
        basic_activity = model.BasicActivity(
            env=my_env,
            name="Basic activity",
            registry=registry,
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            duration=14,
            additional_logs=[reporting_activity],
        )
        model.register_processes([basic_activity])
        my_env.run()

        assert my_env.now == 14
        assert_log(reporting_activity)
        assert_log(basic_activity)
