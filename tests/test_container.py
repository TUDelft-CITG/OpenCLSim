"""Test module for the openclsim container."""

import simpy

from openclsim import core


def test_put_available():
    """Test put available."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize_container([{"id": "default", "capacity": 10, "level": 5}])

    def process():
        at_most_5 = container.get_container_event(level=5, opp="le")
        at_most_6 = container.get_container_event(level=6, opp="le")
        at_most_3 = container.get_container_event(level=3, opp="le")

        assert at_most_5.triggered, "a"
        assert at_most_6.triggered, "b"
        assert not at_most_3.triggered, "c"

        yield from container.get(1)
        at_most_3 = container.get_container_event(level=3, opp="le")
        assert not at_most_3.triggered, "d"

        yield from container.put(1)
        at_most_3 = container.get_container_event(level=3, opp="le")
        assert not at_most_3.triggered, "e"

        yield from container.get(2)
        at_most_3 = container.get_container_event(level=3, opp="le")
        assert at_most_3.triggered, "f"

    env.process(process())
    env.run()


def test_get_available():
    """Test get available."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize_container([{"id": "default", "capacity": 10, "level": 5}])

    def process():
        at_least_5 = container.get_container_event(level=5, opp="ge")
        at_least_4 = container.get_container_event(level=4, opp="ge")
        at_least_7 = container.get_container_event(level=7, opp="ge")

        assert at_least_5.triggered, "a"
        assert at_least_4.triggered, "b"
        assert not at_least_7.triggered, "c"

        yield from container.put(1)
        assert not at_least_7.triggered, "d"

        yield from container.get(1)
        assert not at_least_7.triggered, "e"

        yield from container.put(2)
        assert at_least_7.triggered, "f"

    env.process(process())
    env.run()


def test_empty_full_events():
    """
    Tests the empty_event and full_event properties of openclsim.core.HasContainer.

    Checks whether the events are triggered at the appropriate time.
    """
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize_container([{"id": "default", "capacity": 10, "level": 5}])

    def process():
        empty_event = container.get_empty_event()
        full_event = container.get_full_event()

        assert not empty_event.triggered, "a"
        assert not full_event.triggered, "b"

        yield from container.get(5)
        assert empty_event.triggered, "c"
        assert not full_event.triggered, "d"

        empty_event = container.get_empty_event()
        assert empty_event.triggered, "e"

        yield from container.put(10)
        empty_event = container.get_empty_event()
        assert full_event.triggered, "f"
        assert not empty_event.triggered, "g"

        full_event = container.get_full_event()
        assert full_event.triggered, "h"

        yield from container.get(5)
        full_event = container.get_full_event()
        assert not full_event.triggered, "i"
        assert not empty_event.triggered, "j"

        yield from container.get(5)
        assert empty_event.triggered, "k"

    env.process(process())
    env.run()
