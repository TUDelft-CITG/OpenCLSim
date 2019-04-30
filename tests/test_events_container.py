import pytest
import simpy

from digital_twin import core


def test_events():
    """Tests the empty_event and full_event properties of digital_twin.core.HasContainer.
    Checks whether the events are triggered at the appropriate time."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env, capacity=10, init=5)

    def process():
        empty_event = container.empty_event
        full_event = container.full_event

        assert not empty_event.triggered
        assert not full_event.triggered

        yield container.get(5)
        assert empty_event.triggered
        assert not full_event.triggered

        empty_event = container.empty_event  # creates a new event for if the container is empty again
        assert not empty_event.triggered

        yield container.put(10)
        assert full_event.triggered
        assert not empty_event.triggered

        full_event = container.full_event  # creates a new event for if the container is full again
        assert not full_event.triggered

        yield container.get(5)
        assert not full_event.triggered
        assert not empty_event.triggered

        yield container.get(5)
        assert empty_event.triggered

    env.process(process())
    env.run()
