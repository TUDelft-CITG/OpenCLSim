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
        ),
        {},
    )


# make the movers
@pytest.fixture
def TransportProcessingResource():
    return type(
        "TransportProcessingResource",
        (
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,
        ),
        {},
    )


# Run the test
def test_two_origins_two_destinations(env, Location, TransportProcessingResource):

    # make the locations that have soil
    location = shapely.geometry.Point(0, 0)

    data_from_site = {
        "env": env,  # The simpy environment
        "name": "Location A",  # The name of the "from location"
        "geometry": location,  # The coordinates of the "from location"
        "capacity": 2_500,  # The capacity of the "from location"
        "level": 2_500,  # The actual volume of the "from location"
    }

    data_to_site = {
        "env": env,  # The simpy environment
        "name": "Location B",  # The name of the "to location"
        "geometry": location,  # The coordinates of the "to location"
        "capacity": 2_500,  # The capacity of the "to location"
        "level": 0,  # The actual volume of the "to location"
    }

    from_site = [Location(**data_from_site), Location(**data_from_site)]
    to_site = [Location(**data_to_site), Location(**data_to_site)]

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    data_tpr = {
        "env": env,  # The simpy environment
        "name": "Transport Processing Resource",  # Name
        "geometry": from_site[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity
        "compute_v": compute_v_provider(5, 4.5),
    }  # Variable speed

    processor = TransportProcessingResource(**data_tpr)

    stop_event = []
    stop_event.extend(orig.container.empty_event for orig in from_site)
    stop_event.extend(dest.container.full_event for dest in to_site)
    stop_event = env.all_of(stop_event)

    model.Activity(
        env=env,
        name="Movement of material",
        origin=from_site,
        destination=to_site,
        loader=processor,
        mover=processor,
        unloader=processor,
        stop_event=stop_event,
    )

    env.run()

    assert from_site[0].container.level == 0
    assert from_site[1].container.level == 0

    assert to_site[0].container.level == 2_500
    assert to_site[1].container.level == 2_500
