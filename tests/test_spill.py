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

# make the environment
@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env


# make the locations
@pytest.fixture
def Location():
    return type(
        "Location",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.Locatable,  # Add coordinates to extract distance information and visualize
            core.HasContainer,  # Add information on the material available at the site
            core.HasResource,  # Add information on serving equipment
            core.HasSoil,  # Add soil layers and information
            core.HasSpill,
        ),  # Add tracking of spill
        {},
    )


# make a location with spill requirement
@pytest.fixture
def LocationReq():
    return type(
        "Location",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.Locatable,  # Add coordinates to extract distance information and visualize
            core.HasContainer,  # Add information on the material available at the site
            core.HasResource,  # Add information on serving equipment
            core.HasSoil,  # Add soil layers and information
            core.HasSpillCondition,  # Add limit
            core.HasSpill,
        ),  # Add tracking of spill
        {},
    )


# make the soil objects
@pytest.fixture
def Soil():
    return core.SoilLayer(
        1, 1_000, "Sand", 1_800, 0.1
    )  # layer, volume, type, density, fraction of fines


# make the processors
@pytest.fixture
def Processor():
    return type(
        "Processor", (core.Processor, core.Log, core.Locatable, core.HasPlume), {}
    )


# make the movers
@pytest.fixture
def Mover():
    return type(
        "Mover",
        (
            core.Movable,
            core.Log,
            core.HasResource,
            core.HasContainer,
            core.HasPlume,
            core.HasSoil,
        ),
        {},
    )


"""
Using values from Becker [2014], https://www.sciencedirect.com/science/article/pii/S0301479714005143.

density = the density of the dredged material
fines   = the percentage of fines in the dredged material
volume  = the dredged volume
dredging_duration = duration of the dredging event
overflow_duration = duration of the dredging event whilst overflowing

m_t = total mass of dredged fines per cycle
m_d = total mass of spilled fines during one dredging event
m_h = total mass of dredged fines that enter the hopper

m_o  = total mass of fine material that leaves the hopper during overflow
m_op = total mass of fines that are released during overflow that end in dredging plume
m_r  = total mass of fines that remain within the hopper

m_t = density * fines * volume
m_d = processor.sigma_d * m_t
m_h = m_t - m_d

m_o = (overflow_duration / dredging_duration) * (1 - mover.f_sett) * (1 - mover.f_trap) * m_h
m_op = mover.sigma_o * m_o

Spill dredging = m_d + m_op = (0.015 * 1800 * 0.1 * 1000) + 0 = 2700
Spill placement = m_r * sigma_p = (m_h - m_o) * sigma_p = (m_t - m_d - m_o) * sigma_p = ((1 - 0.015) * 1800 * 0.1 * 1000) * 0.05 = 8865

density = 1800
fines = 0.1
dredging_duration = 1000
overflow_duration = 0
sigma_d=0.015
sigma_o=0.1
sigma_p=0.05
f_sett=0.5
f_trap=0.01
"""

# Test spill with dredging
def test_spill_dredging(env, Location, Processor, Soil):

    # make the locations that have soil
    location = shapely.geometry.Point(0, 0)

    data_from_site = {
        "env": env,  # The simpy environment
        "name": "Location A",  # The name of the "from location"
        "geometry": location,  # The coordinates of the "from location"
        "capacity": 1_000,  # The capacity of the "from location"
        "level": 1_000,
    }  # The actual volume of the "from location"

    from_site = Location(**data_from_site)
    from_site.add_layers(soillayers=[Soil])

    data_to_site = {
        "env": env,  # The simpy environment
        "name": "Location B",  # The name of the "to location"
        "geometry": location,  # The coordinates of the "to location"
        "capacity": 1_000,  # The capacity of the "to location"
        "level": 0,
    }  # The actual volume of the "to location"

    to_site = Location(**data_to_site)

    # make the processor with source terms
    data_processor = {
        "env": env,  # The simpy environment
        "geometry": location,  # The coordinates of the "processore"
        "unloading_func": model.get_unloading_func(
            1
        ),  # Unloading production is 1 amount / s
        "loading_func": model.get_loading_func(1),
    }  # Loading production is 1 amount / s

    processor = Processor(**data_processor)
    processor.ActivityID = "Test activity"

    # Log fuel use of the processor in step 1
    env.process(processor.process(from_site, 0, to_site))
    env.run()
    assert "fines released" in processor.log["Message"]
    fines = [
        processor.log["Value"][i]
        for i in range(len(processor.log["Value"]))
        if processor.log["Message"][i] == "fines released"
    ]
    assert len(fines) == 2
    np.testing.assert_almost_equal(fines[0], 0)
    np.testing.assert_almost_equal(fines[1], 2700)


# Test spill with dredging and placement
def test_spill_placement(env, Location, Mover, Processor, Soil):

    # make the locations that have soil
    location = shapely.geometry.Point(0, 0)

    data_from_site = {
        "env": env,  # The simpy environment
        "name": "Location A",  # The name of the "from location"
        "geometry": location,  # The coordinates of the "from location"
        "capacity": 1_000,  # The capacity of the "from location"
        "level": 1_000,
    }  # The actual volume of the "from location"

    from_site = Location(**data_from_site)
    from_site.add_layers(soillayers=[Soil])

    data_to_site = {
        "env": env,  # The simpy environment
        "name": "Location B",  # The name of the "to location"
        "geometry": location,  # The coordinates of the "to location"
        "capacity": 1_000,  # The capacity of the "to location"
        "level": 0,
    }  # The actual volume of the "to location"

    to_site = Location(**data_to_site)

    # make the processor with source terms
    data_processor = {
        "env": env,  # The simpy environment
        "geometry": location,  # The coordinates of the "processore"
        "unloading_func": model.get_unloading_func(
            1
        ),  # Unloading production is 1 amount / s
        "loading_func": model.get_loading_func(1),
    }  # Loading production is 1 amount / s

    processor = Processor(**data_processor)
    processor.ActivityID = "Test activity"
    processor.rate = lambda x: x / 1

    # make the mover
    data_mover = {
        "env": env,  # The simpy environment
        "v": 1,  # The speed of the mover
        "capacity": 1_000,  # The capacity of the mover container
        "geometry": location,
    }  # The unloading function 1 amount per second

    mover = Mover(**data_mover)
    mover.ActivityID = "Test activity"

    # Log fuel use of the processor in step 1
    env.process(processor.process(mover, 1000, from_site))
    env.run()

    assert "fines released" in processor.log["Message"]
    fines = [
        processor.log["Value"][i]
        for i in range(len(processor.log["Value"]))
        if processor.log["Message"][i] == "fines released"
    ]
    assert len(fines) == 1
    np.testing.assert_almost_equal(fines[0], 2700)

    # Log fuel use of the processor in step 1
    env.process(processor.process(mover, 0, to_site))
    env.run()

    fines = [
        processor.log["Value"][i]
        for i in range(len(processor.log["Value"]))
        if processor.log["Message"][i] == "fines released"
    ]
    assert len(fines) == 2
    np.testing.assert_almost_equal(fines[1], 8865)


# Test spill with requirement
def test_spill_requirement(env, LocationReq, Location, Processor, Soil):

    # make the locations that have soil
    location = shapely.geometry.Point(0, 0)
    limit_start = datetime.datetime(2019, 1, 1)
    limit_end = limit_start + datetime.timedelta(seconds=14 * 24 * 3600)
    condition_1 = core.SpillCondition(100, limit_start, limit_end)

    data_from_site = {
        "env": env,  # The simpy environment
        "name": "Location A",  # The name of the "from location"
        "geometry": location,  # The coordinates of the "from location"
        "capacity": 1_000,  # The capacity of the "from location"
        "level": 1_000,  # The actual volume of the "from location"
        "conditions": [condition_1],
    }  # The spill condition of the "from location"

    from_site = LocationReq(**data_from_site)
    from_site.add_layers(soillayers=[Soil])

    data_to_site = {
        "env": env,  # The simpy environment
        "name": "Location B",  # The name of the "to location"
        "geometry": location,  # The coordinates of the "to location"
        "capacity": 1_000,  # The capacity of the "to location"
        "level": 0,
    }  # The actual volume of the "to location"

    to_site = Location(**data_to_site)

    # make the processor with source terms
    data_processor = {
        "env": env,  # The simpy environment
        "geometry": location,  # The coordinates of the "processore"
        "unloading_func": model.get_unloading_func(
            1
        ),  # Unloading production is 1 amount / s
        "loading_func": model.get_loading_func(1),
    }  # Loading production is 1 amount / s

    processor = Processor(**data_processor)
    processor.ActivityID = "Test activity"
    processor.rate = lambda x: x / 1

    # Log fuel use of the processor in step 1
    env.process(processor.process(from_site, 0, to_site))
    env.run()
    assert processor.log["Message"][0] == "waiting for spill start"

    waiting = processor.log["Timestamp"][1] - processor.log["Timestamp"][0]
    np.testing.assert_almost_equal(waiting.total_seconds(), 14 * 24 * 3600)
