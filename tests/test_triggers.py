"""Test Module for triggers on activities."""

import simpy

import openclsim.model as model


class TestTriggers:
    """Test class for triggers on activities."""

    def test_sequence_triggers(self):
        simulation_start = 0
        env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        a = model.BasicActivity(
            id="a",
            env=env,
            name="a",
            registry=registry,
            duration=1,
        )
        a2 = model.BasicActivity(
            id="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=1,
        )

        c = model.BasicActivity(
            id="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Sa = model.SequentialActivity(
            env=env,
            name="Sa",
            id="Sa",
            registry=registry,
            sub_processes=[a, a2],
        )

        act1 = model.SequentialActivity(
            env=env,
            name="Sc",
            id="Sc",
            registry=registry,
            sub_processes=[c, Sa],
        )

        b = model.BasicActivity(
            id="b",
            env=env,
            name="b",
            registry=registry,
            duration=10,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        act2 = model.SequentialActivity(
            env=env,
            name="Sb",
            id="Sb",
            registry=registry,
            sub_processes=[b],
        )

        model.register_processes([act1, act2])
        env.run()

        assert env.now == 12

    def test_repeat_triggers(self):
        simulation_start = 0
        env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        a = model.BasicActivity(
            id="a",
            env=env,
            name="a",
            registry=registry,
            duration=1,
        )
        a2 = model.BasicActivity(
            id="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=1,
        )
        c = model.BasicActivity(
            id="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Ra = model.RepeatActivity(
            env=env,
            name="Ra",
            id="Ra",
            registry=registry,
            sub_processes=[a, a2],
            repetitions=3,
        )

        act1 = model.SequentialActivity(
            env=env,
            name="Sc",
            id="Sc",
            registry=registry,
            sub_processes=[c, Ra],
        )

        b = model.BasicActivity(
            id="b",
            env=env,
            name="b",
            registry=registry,
            duration=1.5,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        act2 = model.RepeatActivity(
            env=env,
            name="Rb",
            id="Rb",
            registry=registry,
            sub_processes=[b],
            repetitions=3,
        )

        model.register_processes([act1, act2])
        env.run()

        assert env.now == 7.5

    def test_parallel_triggers(self):
        simulation_start = 0
        env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        a = model.BasicActivity(
            id="a",
            env=env,
            name="a",
            registry=registry,
            duration=3,
        )
        a2 = model.BasicActivity(
            id="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=2,
        )
        a3 = model.BasicActivity(
            id="a3",
            env=env,
            name="a3",
            registry=registry,
            duration=5,
        )

        c = model.BasicActivity(
            id="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Pa = model.ParallelActivity(
            env=env,
            name="Pa",
            id="Pa",
            registry=registry,
            sub_processes=[a, a2, a3],
        )

        act1 = model.SequentialActivity(
            env=env,
            name="Sc",
            id="Sc",
            registry=registry,
            sub_processes=[c, Pa],
        )

        b = model.BasicActivity(
            id="b",
            env=env,
            name="b",
            registry=registry,
            duration=10,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        act2 = model.SequentialActivity(
            env=env,
            name="Sb",
            id="Sb",
            registry=registry,
            sub_processes=[b],
        )

        model.register_processes([act1, act2])
        env.run()

        assert env.now == 14
