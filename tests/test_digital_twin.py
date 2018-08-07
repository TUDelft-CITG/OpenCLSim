#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import pytest
import simpy
import shapely.geometry
import logging
import numpy as np

from click.testing import CliRunner

from digital_twin import core
from digital_twin import cli

logger = logging.getLogger(__name__)


@pytest.fixture
def env():
    return simpy.Environment()


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
    assert env.now == 0
