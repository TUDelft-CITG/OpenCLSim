#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import pytest
import simpy
import shapely.geometry
import logging
import datetime
import time
import numpy as np

from click.testing import CliRunner

from digital_twin import core
from digital_twin import cli

logger = logging.getLogger(__name__)


@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env


@pytest.fixture
def geometry_a():
    return shapely.geometry.Point(0, 0)


@pytest.fixture
def geometry_b():
    return shapely.geometry.Point(1, 1)


@pytest.fixture
def locatable_a(geometry_a):
    return core.Locatable(geometry_a)


@pytest.fixture
def locatable_b(geometry_b):
    return core.Locatable(geometry_b)


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert 'digital_twin.cli.main' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output


def test_movable(env, geometry_a, locatable_a, locatable_b):
    movable = core.Movable(v=10, geometry=geometry_a, env=env)
    env.process(movable.move(locatable_b))
    env.run()
    assert movable.geometry.equals(locatable_b.geometry)
    env.process(movable.move(locatable_a))
    env.run()
    assert movable.geometry.equals(locatable_a.geometry)


def test_container_dependent_movable(env, geometry_a, locatable_a, locatable_b):
    v_full = 10
    v_empty = 20
    compute_v = lambda x: x * (v_full - v_empty) + v_empty
    movable = core.ContainerDependentMovable(env=env, geometry=geometry_a, compute_v=compute_v, capacity=10)

    move_and_test(env, locatable_b, movable, 20, 2.18)

    movable.container.put(2)
    move_and_test(env, locatable_a, movable, 18, 2.42)

    movable.container.put(8)
    move_and_test(env, locatable_b, movable, 10, 4.36)

    movable.container.get(10)
    move_and_test(env, locatable_a, movable, 20, 2.18)


def move_and_test(env, destination, movable, expected_speed, expected_time):
    start = env.now
    env.process(movable.move(destination))
    env.run()
    np.testing.assert_almost_equal(movable.current_speed, expected_speed)
    assert movable.geometry.equals(destination.geometry)
    hours_spent = (env.now - start) / 3600
    np.testing.assert_almost_equal(hours_spent, expected_time, decimal=2)


def test_move_to_same_place(env, geometry_a, locatable_a):
    movable = core.Movable(v=10, geometry=geometry_a, env=env)
    env.process(movable.move(locatable_a))
    env.run()
    assert movable.geometry.equals(locatable_a.geometry)
    assert env.now == env.epoch


class BasicStorageUnit(core.HasContainer, core.HasResource, core.Log):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def test_basic_processor(env):
    # move content from one container to another, then move some of it back again
    source = BasicStorageUnit(env=env, capacity=1000, level=1000, nr_resources=1)
    dest = BasicStorageUnit(env=env, capacity=1000, level=0, nr_resources=1)

    processor = core.Processor(env=env, loading_func=(lambda x: x / 2), unloading_func=(lambda x: x / 2))
    processor.rate = processor.loading_func
    processor.geometry = "Test 1"

    env.process(processor.process(source, dest, 600))
    env.run()
    np.testing.assert_almost_equal(env.now, env.epoch + 300)
    assert source.container.level == 400
    assert dest.container.level == 600

    env.process(processor.process(dest, source, 300))
    start = env.now
    env.run()
    time_spent = env.now - start
    np.testing.assert_almost_equal(time_spent, 150)
    assert source.container.level == 700
    assert dest.container.level == 300


def test_dual_processors(env):
    # move content from two different limited containers to an unlimited container at the same time
    limited_container_1 = BasicStorageUnit(env=env, capacity=1000, level=0, nr_resources=1)
    limited_container_2 = BasicStorageUnit(env=env, capacity=1000, level=0, nr_resources=1)
    unlimited_container = BasicStorageUnit(env=env, capacity=2000, level=1000, nr_resources=100)

    processor1 = core.Processor(env=env, loading_func=(lambda x: x / 2), unloading_func=(lambda x: x / 2))
    processor2 = core.Processor(env=env, loading_func=(lambda x: x / 1), unloading_func=(lambda x: x / 1))
    processor1.rate = processor1.loading_func
    processor2.rate = processor2.loading_func
    processor1.geometry = "Test 1"
    processor2.geometry = "Test 2"

    env.process(processor1.process(unlimited_container, limited_container_1, 400))
    env.process(processor2.process(unlimited_container, limited_container_2, 400))
    env.run()

    np.testing.assert_almost_equal(env.now, env.epoch + 400)
    assert unlimited_container.container.level == 200
    assert limited_container_1.container.level == 400
    assert limited_container_2.container.level == 400

    env.process(processor1.process(limited_container_1, unlimited_container, 300))
    env.process(processor2.process(limited_container_2, unlimited_container, 100))
    start = env.now
    env.run()
    time_spent = env.now - start

    np.testing.assert_almost_equal(time_spent, 150)
    assert unlimited_container.container.level == 600
    assert limited_container_1.container.level == 100
    assert limited_container_2.container.level == 300


def test_dual_processors_with_limit(env):
    # move content into a limited container, have two process wait for each other to finish
    unlimited_container_1 = BasicStorageUnit(env=env, capacity=1000, level=1000, nr_resources=100)
    unlimited_container_2 = BasicStorageUnit(env=env, capacity=1000, level=1000, nr_resources=100)
    limited_container = BasicStorageUnit(env=env, capacity=2000, level=0, nr_resources=1)

    processor1 = core.Processor(env=env, loading_func=(lambda x: x / 1), unloading_func=(lambda x: x / 1))
    processor2 = core.Processor(env=env, loading_func=(lambda x: x / 2), unloading_func=(lambda x: x / 2))
    processor1.rate = processor1.loading_func
    processor2.rate = processor2.loading_func
    processor1.geometry = "Test 1"
    processor2.geometry = "Test 2"

    env.process(processor1.process(unlimited_container_1, limited_container, 400))
    env.process(processor2.process(unlimited_container_2, limited_container, 400))
    env.run()

    np.testing.assert_almost_equal(env.now, env.epoch + 600)
    assert limited_container.container.level == 800
    assert unlimited_container_1.container.level == 600
    assert unlimited_container_2.container.level == 600

    env.process(processor1.process(limited_container, unlimited_container_1, 100))
    env.process(processor2.process(limited_container, unlimited_container_2, 300))
    start = env.now
    env.run()
    time_spent = env.now - start

    np.testing.assert_almost_equal(time_spent, 250)
    assert limited_container.container.level == 400
    assert unlimited_container_1.container.level == 700
    assert unlimited_container_2.container.level == 900