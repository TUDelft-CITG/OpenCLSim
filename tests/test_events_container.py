import pytest
import simpy

from digital_twin import core


def test_get_and_put():
    """Tests the get and put methods of digital_twin.core.HasContainer.
    Also uses the level and capacity properties to check the contents of the container."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env, capacity=10, init=0)
    assert container.level == 0
    assert container.capacity == 10

    container.put(5)
    assert container.level == 5

    container.get(3)
    assert container.level == 2

    # getting more than current level or putting more than would fit in the container should raise an error
    with pytest.raises(RuntimeError):
        container.get(20)

    with pytest.raises(RuntimeError):
        container.put(20)


def test_events():
    """Tests the empty_event and full_event properties of digital_twin.core.HasContainer.
    Checks whether the events are triggered at the appropriate time."""
    env = simpy.Environment()
    container = core.EventsContainer(env=env, capacity=10, init=5)

    empty_event = container.empty_event
    full_event = container.full_event

    assert not empty_event.triggered
    assert not full_event.triggered

    container.get(5)
    assert empty_event.triggered
    assert not full_event.triggered

    empty_event = container.empty_event  # creates a new event for if the container is empty again
    assert not empty_event.triggered

    container.put(10)
    assert full_event.triggered
    assert not empty_event.triggered

    full_event = container.full_event  # creates a new event for if the container is full again
    assert not full_event.triggered

    container.get(5)
    assert not full_event.triggered
    assert not empty_event.triggered

    container.get(5)
    assert empty_event.triggered
