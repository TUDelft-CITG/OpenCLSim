#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `openclsim` package."""

import pytest
import simpy
import shapely.geometry
import logging
import datetime
import time
import json
import numpy as np

import matplotlib
from matplotlib.testing.decorators import image_comparison
import matplotlib.pyplot as plt

from click.testing import CliRunner

from openclsim import core
from openclsim import model
from openclsim import plot
from openclsim import cli

logger = logging.getLogger(__name__)


class BasicStorageUnit(core.HasContainer, core.HasResource, core.Locatable, core.Log):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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


@pytest.fixture
def energy_use_sailing():
    return lambda x, y, z: (x / y) * 2 + z * (x / y) * 1


@pytest.fixture
def energy_use_loading():
    return lambda x: x * 4


@pytest.fixture
def energy_use_unloading():
    return lambda x: x * 3


# Test energy use sailing
def test_movable(
    env,
    geometry_a,
    locatable_a,
    locatable_b,
    energy_use_sailing,
    energy_use_loading,
    energy_use_unloading,
):

    mover = type("Mover", (core.Movable, core.EnergyUse, core.Log), {})

    data_mover = {
        "v": 10,
        "geometry": geometry_a,
        "env": env,
        "energy_use_sailing": energy_use_sailing,
        "energy_use_loading": energy_use_loading,
        "energy_use_unloading": energy_use_unloading,
    }

    mover = mover(**data_mover)
    mover.ActivityID = "Test activity"

    # Moving from a to b - energy use should be equal to duration * 2
    start = env.now
    env.process(mover.move(locatable_b))
    env.run()
    np.testing.assert_almost_equal(mover.log["Value"][-2], (env.now - start) * 2)

    # Moving from b to a - energy use should be equal to duration * 2
    start = env.now
    env.process(mover.move(locatable_a))
    env.run()
    np.testing.assert_almost_equal(mover.log["Value"][-2], (env.now - start) * 2)


# Test energy use processing
def test_processor(
    env, geometry_a, energy_use_sailing, energy_use_loading, energy_use_unloading
):

    source = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=1
    )
    dest = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=0, nr_resources=1
    )

    processor = type(
        "processor",
        (
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.EnergyUse,
            core.Locatable,
            core.Log,
        ),
        {},
    )

    data_processor = {
        "env": env,
        "unloading_rate": 2,
        "loading_rate": 2,
        "geometry": geometry_a,
        "energy_use_sailing": energy_use_sailing,
        "energy_use_loading": energy_use_loading,
        "energy_use_unloading": energy_use_unloading,
    }

    processor = processor(**data_processor)
    processor.ActivityID = "Test activity"

    # Log fuel use of the processor in step 1
    start = env.now
    env.process(processor.process(source, 400, dest))
    env.run()

    np.testing.assert_almost_equal(processor.log["Value"][-2], (env.now - start) * 4)

    # Log fuel use of the processor in step 2
    start = env.now
    env.process(processor.process(dest, 300, source))
    env.run()

    np.testing.assert_almost_equal(processor.log["Value"][-2], (env.now - start) * 4)


# Test energy use of a TransportProcessingResource
def test_TransportProcessingResource(
    env,
    geometry_a,
    geometry_b,
    locatable_a,
    locatable_b,
    energy_use_sailing,
    energy_use_loading,
    energy_use_unloading,
):

    source = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=1
    )
    dest = BasicStorageUnit(
        env=env, geometry=geometry_b, capacity=1000, level=0, nr_resources=1
    )

    # The generic class for an object that can move and transport (a TSHD for example)
    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Allow queueing
            core.EnergyUse,
        ),  # Allow logging energy use
        {},
    )

    # TSHD variables
    data_hopper = {
        "env": env,  # The simpy environment
        "name": "Hopper",  # Name
        "geometry": geometry_b,  # It starts at the "to site"
        "loading_rate": 2,  # Loading rate
        "unloading_rate": 1,  # Unloading rate
        "capacity": 500,  # Capacity of the hopper
        "compute_v": lambda x: 1,  # Variable speed
        "energy_use_loading": energy_use_loading,  # Variable fuel use
        "energy_use_sailing": energy_use_sailing,  # Variable fuel use
        "energy_use_unloading": energy_use_unloading,
    }  # Variable fuel use

    # The simulation object
    hopper = TransportProcessingResource(**data_hopper)
    hopper.ActivityID = "Test activity"

    # Simulation starts with moving to A
    start = env.now
    env.process(hopper.move(source))
    env.run()

    # moving empty to energy use is 2 per second
    np.testing.assert_almost_equal(
        hopper.log["Value"][-2], (env.now - start) * 2, decimal=5
    )

    # Simulation continues with loading
    start = env.now
    env.process(hopper.process(hopper, 500, source))
    env.run()

    # Duration should be amount / 2
    # Energy use should be duration * 4
    np.testing.assert_almost_equal(hopper.log["Value"][-3], (env.now - start) * 4)

    # Simulation continues with moving from A to B
    start = env.now
    env.process(hopper.move(locatable_b))
    env.run()

    # moving full so energy use is 3 per second
    np.testing.assert_almost_equal(
        hopper.log["Value"][-2], (env.now - start) * 3, decimal=5
    )

    # Simulation ends with unloading
    hopper.rate = hopper.unloading
    start = env.now
    env.process(hopper.process(hopper, 0, dest))
    env.run()

    np.testing.assert_almost_equal(hopper.log["Value"][-3], (env.now - start) * 3)


# Test energy use of a Processor and ContainerDependentMovable
def test_Processor_ContainerDependentMovable(
    env,
    geometry_a,
    geometry_b,
    locatable_a,
    locatable_b,
    energy_use_sailing,
    energy_use_loading,
    energy_use_unloading,
):

    source = BasicStorageUnit(
        env=env, geometry=geometry_a, capacity=1000, level=1000, nr_resources=1
    )
    dest = BasicStorageUnit(
        env=env, geometry=geometry_b, capacity=1000, level=0, nr_resources=1
    )

    # The generic class for an object that can process (a quay crane for example)
    ProcessingResource = type(
        "ProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Locatable,  # Allow logging of location
            core.Log,  # Allow logging of all discrete events
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.EnergyUse,
        ),  # Add information on fuel
        {},
    )

    processor_1 = {
        "env": env,  # The simpy environment
        "name": "Processor 1",  # Name
        "geometry": geometry_a,  # It is located at location A
        "unloading_rate": 1,  # Unloading rate
        "loading_rate": 2,  # Loading rate
        "energy_use_loading": energy_use_loading,  # Variable fuel use
        "energy_use_sailing": energy_use_sailing,  # Variable fuel use
        "energy_use_unloading": energy_use_loading,
    }  # Variable fuel use
    processor_2 = {
        "env": env,  # The simpy environment
        "name": "Processor 2",  # Name
        "geometry": geometry_b,  # It is located at location B
        "unloading_rate": 1,  # Unloading rate
        "loading_rate": 2,  # Loading rate
        "energy_use_loading": energy_use_unloading,  # Variable fuel use
        "energy_use_sailing": energy_use_sailing,  # Variable fuel use
        "energy_use_unloading": energy_use_unloading,
    }  # Variable fuel use

    # The generic class for an object that can move an amount (a containervessel)
    mover = type(
        "Mover",
        (core.ContainerDependentMovable, core.EnergyUse, core.HasResource, core.Log),
        {},
    )

    data_mover = {
        "compute_v": lambda x: 1,
        "geometry": geometry_a,
        "env": env,
        "capacity": 1000,
        "energy_use_sailing": energy_use_sailing,
        "energy_use_loading": energy_use_loading,
        "energy_use_unloading": energy_use_unloading,
    }

    # The simulation objects
    processor_1 = ProcessingResource(**processor_1)
    processor_2 = ProcessingResource(**processor_2)
    containervessel = mover(**data_mover)

    processor_1.ActivityID = "Test activity"
    processor_2.ActivityID = "Test activity"
    containervessel.ActivityID = "Test activity"

    # Simulation starts with loading
    start = env.now
    env.process(processor_1.process(containervessel, 500, source))
    env.run()

    np.testing.assert_almost_equal(processor_1.log["Value"][-2], (env.now - start) * 4)

    # Simulation continues with moving from A to B
    start = env.now
    env.process(containervessel.move(locatable_b))
    env.run()

    np.testing.assert_almost_equal(
        containervessel.log["Value"][-2], (env.now - start) * 2.5, decimal=5
    )

    # Simulation ends with unloading
    start = env.now
    env.process(processor_2.process(containervessel, 0, dest))
    env.run()

    np.testing.assert_almost_equal(processor_2.log["Value"][-2], (env.now - start) * 3)
