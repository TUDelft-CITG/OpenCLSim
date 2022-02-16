"""Test package."""

import simpy

import openclsim.model as model

from .test_utils import assert_log


class TestBasicActivity:
    """Test class for the basic activity."""

    def test_start_at_timeout(self):
        simulation_start = 0
        my_env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        act = model.BasicActivity(
            env=my_env,
            name="Basic activity",
            registry=registry,
            duration=14,
            start_event={
                "type": "time",
                "start_time": 10,
            },
        )
        model.register_processes([act])
        my_env.run()

        assert my_env.now == 24
        assert_log(act)

    def test_repeat_until_timeout(self):
        simulation_start = 0
        my_env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        basic = model.BasicActivity(
            env=my_env,
            name="Basic activity",
            registry=registry,
            duration=10,
        )

        act = model.WhileActivity(
            env=my_env,
            name="While activity of basic activities",
            registry=registry,
            sub_processes=[basic],
            condition_event={
                "type": "time",
                "start_time": 50,
            },
        )
        model.register_processes([act])
        my_env.run()

        assert my_env.now == 50
        assert_log(act)
        assert_log(basic)
