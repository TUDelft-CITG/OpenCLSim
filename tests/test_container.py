"""Test module for the openclsim container."""

import simpy

from openclsim import core


def test_put_available():
    """Test put available."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize(capacity=10, init=5)

    def process():
        at_most_5 = container.put_available(5)
        assert at_most_5.triggered

        at_most_6 = container.put_available(4)
        assert at_most_6.triggered

        at_most_3 = container.put_available(7)
        assert not at_most_3.triggered

        yield container.get(1)
        assert not at_most_3.triggered

        yield container.put(1)
        assert not at_most_3.triggered

        yield container.get(2)
        assert at_most_3.triggered

    env.process(process())
    env.run()


def test_get_available():
    """Test get available."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize(capacity=10, init=5)

    def process():
        at_least_5 = container.get_available(5)
        assert at_least_5.triggered

        at_least_4 = container.get_available(4)
        assert at_least_4.triggered

        at_least_7 = container.get_available(7)
        assert not at_least_7.triggered

        yield container.put(1)
        assert not at_least_7.triggered

        yield container.get(1)
        assert not at_least_7.triggered

        yield container.put(2)
        assert at_least_7.triggered

    env.process(process())
    env.run()


def test_empty_full_events():
    """
    Tests the empty_event and full_event properties of openclsim.core.HasContainer.

    Checks whether the events are triggered at the appropriate time.
    """
    env = simpy.Environment()
    container = core.EventsContainer(env=env)
    container.initialize(capacity=10, init=5)

    def process():
        empty_event = container.empty_event
        full_event = container.full_event

        assert not empty_event.triggered
        assert not full_event.triggered

        yield container.get(5)
        assert empty_event.triggered
        assert not full_event.triggered

        empty_event = container.empty_event
        assert empty_event.triggered

        yield container.put(10)
        empty_event = container.empty_event
        assert full_event.triggered
        assert not empty_event.triggered

        full_event = container.full_event
        assert full_event.triggered

        yield container.get(5)
        full_event = container.full_event
        assert not full_event.triggered
        assert not empty_event.triggered

        yield container.get(5)
        assert empty_event.triggered

    env.process(process())
    env.run()
