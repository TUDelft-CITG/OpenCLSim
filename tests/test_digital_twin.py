#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import pytest
import simpy
import shapely.geometry
import logging

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
