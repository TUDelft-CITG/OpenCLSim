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
            ID="a",
            env=env,
            name="a",
            registry=registry,
            duration=1,
        )
        a2 = model.BasicActivity(
            ID="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=1,
        )

        c = model.BasicActivity(
            ID="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Sa = model.SequentialActivity(
            env=env,
            name="Sa",
            ID="Sa",
            registry=registry,
            sub_processes=[a, a2],
        )

        model.SequentialActivity(
            env=env,
            name="Sc",
            ID="Sc",
            registry=registry,
            sub_processes=[c, Sa],
        )

        b = model.BasicActivity(
            ID="b",
            env=env,
            name="b",
            registry=registry,
            duration=10,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        model.SequentialActivity(
            env=env,
            name="Sb",
            ID="Sb",
            registry=registry,
            sub_processes=[b],
        )

        env.run()

        assert env.now == 12

    def test_repeat_triggers(self):
        simulation_start = 0
        env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        a = model.BasicActivity(
            ID="a",
            env=env,
            name="a",
            registry=registry,
            duration=1,
        )
        a2 = model.BasicActivity(
            ID="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=1,
        )
        c = model.BasicActivity(
            ID="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Ra = model.RepeatActivity(
            env=env,
            name="Ra",
            ID="Ra",
            registry=registry,
            sub_processes=[a, a2],
            repetitions=3,
        )

        model.SequentialActivity(
            env=env,
            name="Sc",
            ID="Sc",
            registry=registry,
            sub_processes=[c, Ra],
        )

        b = model.BasicActivity(
            ID="b",
            env=env,
            name="b",
            registry=registry,
            duration=1.5,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        model.RepeatActivity(
            env=env,
            name="Rb",
            ID="Rb",
            registry=registry,
            sub_processes=[b],
            repetitions=3,
        )

        env.run()

        assert env.now == 7.5

    def test_parallel_triggers(self):
        simulation_start = 0
        env = simpy.Environment(initial_time=simulation_start)
        registry = {}

        a = model.BasicActivity(
            ID="a",
            env=env,
            name="a",
            registry=registry,
            duration=3,
        )
        a2 = model.BasicActivity(
            ID="a2",
            env=env,
            name="a2",
            registry=registry,
            duration=2,
        )
        a3 = model.BasicActivity(
            ID="a3",
            env=env,
            name="a3",
            registry=registry,
            duration=5,
        )

        c = model.BasicActivity(
            ID="c",
            env=env,
            name="c",
            registry=registry,
            duration=1,
        )

        Pa = model.ParallelActivity(
            env=env,
            name="Pa",
            ID="Pa",
            registry=registry,
            sub_processes=[a, a2, a3],
        )

        model.SequentialActivity(
            env=env,
            name="Sc",
            ID="Sc",
            registry=registry,
            sub_processes=[c, Pa],
        )

        b = model.BasicActivity(
            ID="b",
            env=env,
            name="b",
            registry=registry,
            duration=10,
            start_event=[{"name": "a", "type": "activity", "state": "done"}],
        )

        model.SequentialActivity(
            env=env,
            name="Sb",
            ID="Sb",
            registry=registry,
            sub_processes=[b],
        )

        env.run()

        assert env.now == 14
