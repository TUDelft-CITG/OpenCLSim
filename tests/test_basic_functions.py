"""Tests for `openclsim` package."""

import datetime
import logging
import time

import numpy as np
import pytest
import shapely.geometry
import simpy

from openclsim import core

logger = logging.getLogger(__name__)


@pytest.fixture
def env():
    """Fixture for the environment."""
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env


@pytest.fixture
def geometry_a():
    """Fixture for the geometry_a."""
    return shapely.geometry.Point(0, 0)


@pytest.fixture
def geometry_b():
    """Fixture for the geometry_b."""
    return shapely.geometry.Point(1, 1)


@pytest.fixture
def locatable_a(geometry_a):
    """Fixture for the locatable_a."""
    return core.Locatable(geometry_a)


@pytest.fixture
def locatable_b(geometry_b):
    """Fixture for the locatable_b."""
    return core.Locatable(geometry_b)


def test_movable(env, geometry_a, locatable_a, locatable_b):
    """Test movable."""

    class Movable(core.Movable, core.Log):
        pass

    movable = Movable(env=env, geometry=geometry_a, v=10)
    movable.activity_id = "Test activity"
    env.process(movable.move(locatable_b))
    env.run()
    assert movable.geometry.equals(locatable_b.geometry)
    env.process(movable.move(locatable_a))
    env.run()
    assert movable.geometry.equals(locatable_a.geometry)


def test_container_dependent_movable(env, geometry_a, locatable_a, locatable_b):
    """Test container dependent movable."""
    v_full = 10
    v_empty = 20

    def compute_v(x):
        return x * (v_full - v_empty) + v_empty

    class Movable(core.ContainerDependentMovable, core.Log):
        pass

    movable = Movable(env=env, geometry=geometry_a, compute_v=compute_v, capacity=10)
    movable.activity_id = "Test activity"

    move_and_test(env, locatable_b, movable, 20, 2.18)

    movable.container.put(2)
    move_and_test(env, locatable_a, movable, 18, 2.42)

    movable.container.put(8)
    move_and_test(env, locatable_b, movable, 10, 4.36)

    movable.container.get(10)
    move_and_test(env, locatable_a, movable, 20, 2.18)


def move_and_test(env, destination, movable, expected_speed, expected_time):
    """Move and test."""
    start = env.now
    env.process(movable.move(destination))
    env.run()
    np.testing.assert_almost_equal(movable.v, expected_speed)
    assert movable.geometry.equals(destination.geometry)
    hours_spent = (env.now - start) / 3600
    np.testing.assert_almost_equal(hours_spent, expected_time, decimal=2)


def test_move_to_same_place(env, geometry_a, locatable_a):
    """Test move to same place."""

    class movable(core.Movable, core.Log):
        pass

    movable = movable(env=env, geometry=geometry_a, v=10)
    movable.activity_id = "Test activity"

    env.process(movable.move(locatable_a))
    env.run()
    assert movable.geometry.equals(locatable_a.geometry)
    assert env.now == env.epoch


class BasicStorageUnit(core.HasContainer, core.HasResource, core.Locatable, core.Log):
    """Basic storage unit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "BasicStorageUnit"


class Processor(
    core.Processor,
    core.LoadingFunction,
    core.UnloadingFunction,
    core.Log,
    core.Locatable,
):
    """Test class for the processor."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@pytest.mark.skip
def test_basic_processor(env, geometry_a):
    """Test basic processor."""
    source = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=1
    )
    dest = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=0, nr_resources=1
    )

    processor = Processor(
        env=env, loading_rate=2, unloading_rate=2, geometry=geometry_a
    )

    processor.activity_id = "Test activity"

    env.process(processor.process(source, 400, dest))
    env.run()
    np.testing.assert_almost_equal(env.now, env.epoch + 300)
    assert source.container.get_level() == 400
    assert dest.container.get_level() == 600

    env.process(processor.process(dest, 300, source))
    start = env.now
    env.run()
    time_spent = env.now - start
    np.testing.assert_almost_equal(time_spent, 150)
    assert source.container.get_level() == 700
    assert dest.container.get_level() == 300
