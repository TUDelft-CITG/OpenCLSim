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
import dill as pickle

from click.testing import CliRunner

from digital_twin import core
from digital_twin import model
from digital_twin import cli
from digital_twin import savesim

logger = logging.getLogger(__name__)

# The generic class for an object that can store an amount (a stockpile for example)
class BasicStorageUnit(core.HasContainer, core.Identifiable, core.HasResource, core.Locatable, core.Log):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# The generic class for an object that can process (a quay crane for example)
class ProcessingResource(core.Identifiable, core.Locatable, core.Log, core.Processor, core.HasResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# The generic class for an object that can move an amount (a containervessel for example)
class Mover(core.ContainerDependentMovable, core.Identifiable, core.HasResource, core.Log):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# The basic environment variables are listed below
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
def compute_v_provider():
    return lambda x: x * (1 - 1) + 1

@pytest.fixture
def compute_loading():
    return lambda current_level, desired_level: (desired_level - current_level) / 1

@pytest.fixture
def compute_unloading():
    return lambda current_level, desired_level: (current_level - desired_level) / 1

"""

Actual testing starts below

"""

def test_savesim(env, geometry_a, geometry_b, compute_v_provider, compute_loading, compute_unloading):

    # Initialize the origin
    data_origin = {"env": env, 
                   "name": "origin",
                   "geometry": geometry_a, 
                   "capacity": 1000, 
                   "level": 1000}
    origin = BasicStorageUnit(**data_origin)

    # Initialize the destination
    data_destination = {"env": env, 
                        "name": "destination",
                        "geometry": geometry_b, 
                        "capacity": 1000, 
                        "level": 0}
    destination = BasicStorageUnit(**data_destination)

    # Initialize the loader
    data_loader = {"env": env, 
                   "name": "loader",
                   "geometry": geometry_a, 
                   "loading_func": compute_loading, 
                   "unloading_func": compute_unloading}
    loader = ProcessingResource(**data_loader)

    # Initialize the unloader
    data_unloader = {"env": env, 
                     "name": "unloader",
                     "geometry": geometry_b, 
                     "loading_func": compute_loading, 
                     "unloading_func": compute_unloading}
    unloader = ProcessingResource(**data_unloader)
    
    # Initialize the mover
    data_mover = {"env": env, 
                  "name": "Mover",
                  "geometry": geometry_a, 
                  "capacity": 1000, 
                  "compute_v": compute_v_provider}
    mover = Mover(**data_mover)
    
    # Initialize the activity
    activity = model.Activity(env = env,
                              name = "Move amount",
                              origin = origin,
                              destination = destination,
                              loader = loader,
                              mover = mover,
                              unloader = unloader)

    # Save the simulation variables
    save_origin = savesim.ToSave(BasicStorageUnit, data_origin)
    save_destination = savesim.ToSave(BasicStorageUnit, data_destination)

    save_loader = savesim.ToSave(ProcessingResource, data_loader)
    save_unloader = savesim.ToSave(ProcessingResource, data_unloader)
    save_mover = savesim.ToSave(Mover, data_mover)

    save_activity = savesim.ToSave(model.Activity, activity.__dict__)

    simulation = savesim.SimulationSave(env, [save_activity], [save_loader, save_unloader, save_mover], [save_origin, save_destination])
    simulation.save_ini_file("Simulation test_savesim")

    # Run the simulation
    env.run()

    
    # Open the .pkl file and run the simulation
    simulation = savesim.SimulationOpen("Simulation test_savesim.pkl")
    sites, equipment, activities, environment = simulation.extract_files()
    environment.run()

    # Assert all original logs are equal to those from the simulation that started with the .pkl file
    assert loader.log == equipment[0].log
    assert unloader.log == equipment[1].log
    assert mover.log == equipment[2].log
    
    assert origin.log == sites[0].log
    assert destination.log == sites[1].log
    
    assert activity.log == activities[0].log