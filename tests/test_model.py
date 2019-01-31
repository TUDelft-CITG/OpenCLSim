#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import pytest
import simpy
import shapely.geometry
import logging
import datetime
import time
import pyproj
import numpy as np

from click.testing import CliRunner

from digital_twin import model
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
def location():
    Site = type('Site', (core.Identifiable, # Give it a name
                        core.Log,           # Allow logging of all discrete events
                        core.Locatable,     # Add coordinates to extract distance information and visualize
                        core.HasContainer,  # Add information on the material available at the site
                        core.HasResource),  # Add information on serving equipment
                {})                         # The dictionary is empty because the site type is generic
    
    return Site


@pytest.fixture
def TransportProcessing():
    TransportProcessingResource = type('TransportProcessingResource', 
                                       (core.Identifiable,              # Give it a name
                                        core.Log,                       # Allow logging of all discrete events
                                        core.ContainerDependentMovable, # A moving container, so capacity and location
                                        core.Processor,                 # Allow for loading and unloading
                                        core.HasResource),              # Add information on serving equipment
                                    {})
    
    return TransportProcessingResource


# Test model with one trip - transporting an amount with "Vessel 01" from "From Site" to "To Site"
def test_model_one_trip(env, location, TransportProcessing):

    # make the site objects
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat
    location_to_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat

    data_from_site = {"env": env,                     # The simpy environment defined in the first cel
                      "name": "From Site",            # The name of the site
                      "geometry": location_from_site, # The coordinates of the project site
                      "capacity": 1_000,              # The capacity of the site
                      "level": 1_000}                 # The actual volume of the site
    data_to_site = {"env": env,                     # The simpy environment defined in the first cel
                    "name": "To Site",              # The name of the site
                    "geometry": location_to_site,   # The coordinates of the project site
                    "capacity": 1_000,              # The capacity of the site
                    "level": 0}                     # The actual volume of the site

    from_site = location(**data_from_site)
    to_site   = location(**data_to_site)

    # make the transportprocessingresource
    data_vessel = {"env": env,                        # The simpy environment 
                   "name": "Vessel 01",               # Name
                   "geometry": location_from_site,    # It starts at the "from site"
                   "unloading_func": (lambda x: x),   # Unloading production is 1 amount / s
                   "loading_func": (lambda x: x),     # Loading production is 1 amount / s
                   "capacity": 1_000,                 # Capacity of the vessel
                   "compute_v": (lambda x: 1)}        # Speed is always 1 m / s

    vessel = TransportProcessing(**data_vessel)

    # make the activity
    activity = model.Activity(env = env,           # The simpy environment defined in the first cel
                              name = "Moving amount", # We are moving soil
                              origin = from_site,     # We originate from the from_site
                              destination = to_site,  # And therefore travel to the to_site
                              loader = vessel,        # The benefit of a TSHD, all steps can be done
                              mover = vessel,         # The benefit of a TSHD, all steps can be done
                              unloader = vessel,      # The benefit of a TSHD, all steps can be done
                              start_condition = None) # We can start right away and do not stop
    
    # run the activity
    start = env.now
    env.run()

    # Duration of the activity should be equal to loading + sailing + unloading + sailing
    # -- Loading duration is equal to the amount
    # -- Unloading duration is equal to the amount
    # -- Sailing duration is equal to the distance travelled
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_site.geometry)
    dest = shapely.geometry.asShape(to_site.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    np.testing.assert_almost_equal(env.now - start, 2 * 1000 + 2 * distance)