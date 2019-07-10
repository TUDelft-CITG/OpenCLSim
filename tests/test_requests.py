#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `openclsim` package."""

import pytest
import simpy
import shapely.geometry
import logging
import datetime
import time
import numpy as np

from click.testing import CliRunner

from openclsim import core
from openclsim import model
from openclsim import cli

logger = logging.getLogger(__name__)


@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
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


class BasicStorageUnit(core.HasContainer, core.HasResource, core.Locatable, core.Log):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Processor(
    core.Processor,
    core.LoadingFunction,
    core.UnloadingFunction,
    core.Log,
    core.Locatable,
    core.HasResource,
    core.Identifiable,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_dual_processors(env, geometry_a):
    # move content from two different limited containers to an unlimited container at the same time
    limited_container_1 = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=0, nr_resources=1
    )
    limited_container_2 = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=0, nr_resources=1
    )
    unlimited_container = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=2000, level=1000, nr_resources=100
    )

    processor1 = Processor(
        env=env,
        name="Processor 1",
        loading_rate=2,
        unloading_rate=2,
        geometry=geometry_a,
    )
    processor2 = Processor(
        env=env,
        name="Processor 2",
        loading_rate=1,
        unloading_rate=1,
        geometry=geometry_a,
    )

    processor1.ActivityID = "Test activity"
    processor2.ActivityID = "Test activity"

    env.process(processor1.process(limited_container_1, 400, unlimited_container))
    env.process(processor2.process(limited_container_2, 400, unlimited_container))
    env.run()

    np.testing.assert_almost_equal(env.now, env.epoch + 400)
    assert unlimited_container.container.level == 200
    assert limited_container_1.container.level == 400
    assert limited_container_2.container.level == 400

    env.process(processor1.process(limited_container_1, 100, unlimited_container))
    env.process(processor2.process(limited_container_2, 300, unlimited_container))
    start = env.now
    env.run()
    time_spent = env.now - start

    np.testing.assert_almost_equal(time_spent, 150)
    assert unlimited_container.container.level == 600
    assert limited_container_1.container.level == 100
    assert limited_container_2.container.level == 300


def test_dual_processors_with_limit(env, geometry_a):
    # move content into a limited container, have two process wait for each other to finish
    unlimited_container_1 = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=100
    )
    unlimited_container_2 = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=100
    )
    unlimited_container_3 = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=2000, level=0, nr_resources=100
    )
    limited_container = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=2000, level=0, nr_resources=1
    )

    processor1 = Processor(
        env=env,
        name="Processor 1",
        loading_rate=1,
        unloading_rate=1,
        geometry=geometry_a,
    )
    processor2 = Processor(
        env=env,
        name="Processor 2",
        loading_rate=1,
        unloading_rate=1,
        geometry=geometry_a,
    )

    processor1.ActivityID = "Test activity"
    processor2.ActivityID = "Test activity"

    env.process(
        model.single_run_process(
            processor1,
            env,
            unlimited_container_1,
            limited_container,
            processor1,
            unlimited_container_3,
            processor1,
        )
    )
    env.process(
        model.single_run_process(
            processor2,
            env,
            unlimited_container_2,
            limited_container,
            processor2,
            unlimited_container_3,
            processor2,
        )
    )
    env.run()

    # Simultaneous accessing limited_container, so waiting event of 1000 seconds
    np.testing.assert_almost_equal(env.now, env.epoch + 3000)
    assert limited_container.container.level == 2000
    assert unlimited_container_1.container.level == 0
    assert unlimited_container_2.container.level == 0
