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
import pandas as pd

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


@pytest.fixture
def weather_data():
    df = pd.read_csv("tests/test_weather.csv")
    df.index = df[["Year", "Month", "Day", "Hour"]].apply(
        lambda s: datetime.datetime(*s), axis=1
    )
    df = df.drop(["Year", "Month", "Day", "Hour"], axis=1)
    return df


# make a location with metocean data
@pytest.fixture
def LocationWeather():
    return type(
        "Location with Metocean",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.Locatable,  # Add coordinates to extract distance information and visualize
            core.HasContainer,  # Add information on the material available at the site
            core.HasResource,  # Add information on serving equipment
            core.HasWeather,
        ),  # Add information on metocean data
        {},
    )


# make a location without metocean data
@pytest.fixture
def Location():
    return type(
        "Location without Metocean",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.Locatable,  # Add coordinates to extract distance information and visualize
            core.HasContainer,  # Add information on the material available at the site
            core.HasResource,
        ),  # Add information on serving equipment
        {},
    )


# make the processors
@pytest.fixture
def Processor():
    return type(
        "Processor",
        (
            core.Identifiable,
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.Log,
            core.Locatable,
        ),
        {},
    )


# make the movers
@pytest.fixture
def Mover():
    return type(
        "Mover",
        (
            core.Identifiable,
            core.Movable,
            core.Log,
            core.HasResource,
            core.HasContainer,
            core.HasDepthRestriction,
        ),
        {},
    )


# Test calculating restrictions
def test_calc_restrictions(
    env, geometry_a, Mover, Processor, LocationWeather, weather_data
):

    # Initialize the Mover
    def compute_draught(draught_empty, draught_full):
        return lambda x: x * (draught_full - draught_empty) + draught_empty

    data = {
        "env": env,  # The simpy environment
        "name": "Vessel",  # Name
        "geometry": geometry_a,  # Location
        "capacity": 7_200,  # Capacity of the hopper - "Beunvolume"
        "v": 1,  # Speed always 1 m/s
        "compute_draught": compute_draught(4.0, 7.0),  # Variable draught
        "waves": [0.5, 1],  # Waves with specific ukc
        "ukc": [0.75, 1],  # UKC corresponding to the waves
        "filling": None,
    }  # The filling degree

    mover = Mover(**data)
    mover.ActivityID = "Test activity"

    data = {
        "env": env,  # The simpy environment
        "name": "Quay Crane",  # Name
        "geometry": geometry_a,  # It starts at the "from site"
        "loading_rate": 1,  # Loading rate
        "unloading_rate": 1,
    }  # Unloading rate

    crane = Processor(**data)
    crane.ActivityID = "Test activity"
    crane.rate = crane.loading

    # Initialize the LocationWeather
    data = {
        "env": env,  # The simpy environment defined in the first cel
        "name": "Limited Location",  # The name of the site
        "geometry": geometry_a,  # Location
        "capacity": 500_000,  # The capacity of the site
        "level": 500_000,  # The actual volume of the site
        "dataframe": weather_data,  # The dataframe containing the weather data
        "bed": -7,
    }  # The level of the seabed with respect to CD

    location = LocationWeather(**data)

    # Test weather data at site
    # The bed level is at CD -7, the tide is at CD. thus the water depth is 7 meters
    assert location.metocean_data["Water depth"][0] == 7
    # The timeseries start is equal to the simulation start
    assert location.metocean_data.index[0] == datetime.datetime.fromtimestamp(env.now)

    # Test calculated restrictions
    mover.calc_depth_restrictions(location, crane)
    assert mover.depth_data[location.name][0.5]["Volume"] == 3_600
    assert mover.depth_data[location.name][0.5]["Draught"] == 5.5

    # Test current draught of the mover (empty)
    assert mover.current_draught == 4.0

    # Process an amount of 3_600 from the location into the mover
    # This takes 3_600 seconds and should be able to start right away
    start = env.now
    env.process(crane.process(site=location, ship=mover, desired_level=3_600))
    env.run()

    np.testing.assert_almost_equal(env.now, start + 3_600)

    # Step forward to 18:00
    def step_forward(env):
        yield env.timeout(17 * 3600)

    env.process(step_forward(env))
    env.run()

    # Process an amount of 3_600 from the location into the mover
    # This takes 3_600 seconds and cannot start right away due to tide restrictions
    start = env.now
    assert datetime.datetime.fromtimestamp(env.now) == datetime.datetime(2019, 1, 1, 18)
    assert (
        location.metocean_data["Water depth"][datetime.datetime(2019, 1, 1, 21)] == 6.5
    )
    assert mover.container.level / mover.container.capacity in list(
        mover.depth_data[location.name].keys()
    )

    env.process(crane.process(ship=mover, site=location, desired_level=0))
    env.run()

    # There should be 3 hours of waiting, 1 hour of processing, so time should be start + 4 hours
    np.testing.assert_almost_equal(env.now, start + 3_600 + 3 * 3_600)


# Test optimal filling
# Every 4th hour dredging not possible
# sailing 2x 1 hour, dredging + dumping 1 hour, to get cycle with continous "optimal degree at 50%"
