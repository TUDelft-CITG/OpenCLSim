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
import dill as pickle
import json


from click.testing import CliRunner

from openclsim import core
from openclsim import model
from openclsim import cli
from openclsim import savesim
from openclsim import io

logger = logging.getLogger(__name__)

# The generic class for an object that can store an amount (a stockpile for example)
class BasicStorageUnit(
    core.HasContainer, core.Identifiable, core.HasResource, core.Locatable, core.Log
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# The generic class for an object that can process (a quay crane for example)
class ProcessingResource(
    core.Identifiable, core.Locatable, core.Log, core.Processor, core.HasResource
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# The generic class for an object that can move an amount (a containervessel for example)
class Mover(
    core.ContainerDependentMovable, core.Identifiable, core.HasResource, core.Log
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# The basic environment variables are listed below
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
def compute_v_provider():
    return lambda x: x * (1 - 1) + 1


@pytest.fixture
def compute_loading():
    return lambda current_level, desired_level: (desired_level - current_level) / 1


@pytest.fixture
def compute_unloading():
    return lambda current_level, desired_level: (current_level - desired_level) / 1


@pytest.fixture
def loader(env, geometry_a, compute_loading, compute_unloading):
    # Initialize the loader
    data_loader = {
        "env": env,
        "name": "loader",
        "geometry": geometry_a,
        "loading_func": compute_loading,
        "unloading_func": compute_unloading,
    }
    loader = ProcessingResource(**data_loader)
    return loader


@pytest.fixture
def unloader(env, geometry_b, compute_loading, compute_unloading):
    # Initialize the unloader
    data_unloader = {
        "env": env,
        "name": "unloader",
        "geometry": geometry_b,
        "loading_func": compute_loading,
        "unloading_func": compute_unloading,
    }
    unloader = ProcessingResource(**data_unloader)
    return unloader


@pytest.fixture
def mover(env, geometry_a, compute_v_provider):
    # Initialize the mover
    data_mover = {
        "env": env,
        "name": "Mover",
        "geometry": geometry_a,
        "capacity": 1000,
        "compute_v": compute_v_provider,
    }
    mover = Mover(**data_mover)
    return mover


@pytest.fixture
def origin(env, geometry_a):
    # Initialize the origin
    data_origin = {
        "env": env,
        "name": "origin",
        "geometry": geometry_a,
        "capacity": 1000,
        "level": 1000,
    }
    origin = BasicStorageUnit(**data_origin)
    return origin


@pytest.fixture
def destination(env, geometry_b):
    # Initialize the destination
    data_destination = {
        "env": env,
        "name": "destination",
        "geometry": geometry_b,
        "capacity": 1000,
        "level": 0,
    }
    destination = BasicStorageUnit(**data_destination)
    return destination


@pytest.fixture
def activity(env, origin, destination, loader, mover, unloader):
    # Initialize the activity
    activity = model.Activity(
        env=env,
        name="Move amount",
        origin=origin,
        destination=destination,
        loader=loader,
        mover=mover,
        unloader=unloader,
    )
    return activity


"""

Actual testing starts below

"""


def test_savesim(env, origin, destination, loader, unloader, mover, activity, tmpdir):
    simulation = {
        "env": env,
        "locations": [origin, destination],
        "equipment": [loader, mover, unloader],
        "activities": [activity],
    }
    io.save(simulation, tmpdir / "Simulation test_savesim.json")

    assert (tmpdir / "Simulation test_savesim.json").exists()


@pytest.mark.skip(reason="saving to pickle is broken")
def test_loadsim(loader, unloader, mover, shared_datadir):

    # Open the .pkl file and run the simulation
    simulation = savesim.SimulationOpen(shared_datadir / "Simulation test_savesim.pkl")
    sites, equipment, activities, environment = simulation.extract_files()
    environment.run()

    # Assert all original logs are equal to those from the simulation that started with the .pkl file
    # TODO: this does not work, at least not cross computer.
    assert loader.log == equipment[0].log
    assert unloader.log == equipment[1].log
    assert mover.log == equipment[2].log

    assert origin.log == sites[0].log
    assert destination.log == sites[1].log

    assert activity.log == activities[0].log

    # Test writing the log files to .csv
    savesim.LogSaver(
        sites,
        equipment,
        activities,
        simulation_id="1ad9cb7a-4570-11e9-9c61-b469212bff5b",
        simulation_name="test_savesim",
        location="tests/results",
        overwrite=True,
    )

    # Test if error is raised
    # savesim.LogSaver(sites, equipment, activities,
    #                  simulation_id = '1ad9cb7a-4570-11e9-9c61-b469212bff5b', simulation_name = "test_savesim",
    #                  location = "tests/results")
