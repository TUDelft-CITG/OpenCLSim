#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import datetime
import logging
import time

import numpy as np
import pytest
import pyproj
import shapely.geometry
import simpy

from digital_twin import model
from digital_twin import core

logger = logging.getLogger(__name__)

# make the environment
@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env

# make the fixed locations
@pytest.fixture
def geometry_a():
    return shapely.geometry.Point(4.18055556, 52.18664444)


@pytest.fixture
def geometry_b():
    return shapely.geometry.Point(4.18055556, 52.18664444)

# make the location objects
@pytest.fixture
def Location():
    return type('Location', (core.Identifiable, # Give it a name
                    core.Log,           # Allow logging of all discrete events
                    core.Locatable,     # Add coordinates to extract distance information and visualize
                    core.HasContainer,  # Add information on the material available at the site
                    core.HasResource),  # Add information on serving equipment
            {})                         # The dictionary is empty because the site type is generic

# make the transportprocessingresource
@pytest.fixture
def TransportProcessingResource():
    return type('TransportProcessingResource', 
                                    (core.Identifiable,             # Give it a name
                                    core.Log,                       # Allow logging of all discrete events
                                    core.ContainerDependentMovable, # A moving container, so capacity and location
                                    core.Processor,                 # Allow for loading and unloading
                                    core.HasResource),              # Add information on serving equipment
                                {})


# Test model with one trip - transporting an amount with "Vessel 01" from "From Site" to "To Site"
def test_model_one_trip(env, geometry_a, geometry_b, Location, TransportProcessingResource):
    amount = 1_000
    
    # Initialize from site with correct parameters
    data_from_location = {"env": env,                       # The simpy environment
                          "name": "Location A",             # The name of the "from location"
                          "geometry": geometry_a,   # The coordinates of the "from location"
                          "capacity": amount,               # The capacity of the "from location"
                          "level": amount}                  # The actual volume of the "from location"
    data_to_location = {  "env": env,                       # The simpy environment
                          "name": "Location B",             # The name of the "to location"
                          "geometry": geometry_b,     # The coordinates of the "to location"
                          "capacity": amount,               # The capacity of the "to location"
                          "level": 0}                       # The actual volume of the "to location"

    from_location = Location(**data_from_location)
    to_location = Location(**data_to_location)

    # make the vessel
    data_vessel = {"env": env,                     # The simpy environment 
                "name": "Vessel 01",               # Name of the vessel
                "geometry": geometry_a,            # It is located at the "from location"
                "unloading_func": model.get_unloading_func(1),   # Unloading production is 1 amount / s
                "loading_func": model.get_loading_func(1),     # Loading production is 1 amount / s
                "capacity": 1_000,                 # Capacity of the vessel
                "compute_v": (lambda x: 1)}        # Speed is always 1 m / s

    vessel = TransportProcessingResource(**data_vessel)
    
    # make the activity
    model.Activity(env = env,                   # The simpy environment defined in the first cel
                   name = "Moving amount",      # We are moving soil
                   origin = from_location,      # We originate from the from_site
                   destination = to_location,   # And therefore travel to the to_site
                   loader = vessel,             # The benefit of a TSHD, all steps can be done
                   mover = vessel,              # The benefit of a TSHD, all steps can be done
                   unloader = vessel)           # The benefit of a TSHD, all steps can be done

    # run the activity
    start = env.now
    env.run()

    # Duration of the activity should be equal to loading + sailing + unloading + sailing
    # -- Loading duration is equal to the amount
    # -- Unloading duration is equal to the amount
    # -- Sailing duration is equal to the distance travelled
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_location.geometry)
    dest = shapely.geometry.asShape(to_location.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    np.testing.assert_almost_equal(env.now - start, 2 * 1000 + 2 * distance)


# Test model with multiple trips
def test_model_multiple_trips(env, geometry_a, geometry_b, Location, TransportProcessingResource):
    amount = 10_000
    
    # Initialize from site with correct parameters
    data_from_location = {"env": env,                       # The simpy environment
                          "name": "Location A",             # The name of the "from location"
                          "geometry": geometry_a,   # The coordinates of the "from location"
                          "capacity": amount,               # The capacity of the "from location"
                          "level": amount}                  # The actual volume of the "from location"
    data_to_location = {  "env": env,                       # The simpy environment
                          "name": "Location B",             # The name of the "to location"
                          "geometry": geometry_b,     # The coordinates of the "to location"
                          "capacity": amount,               # The capacity of the "to location"
                          "level": 0}                       # The actual volume of the "to location"

    from_location = Location(**data_from_location)
    to_location = Location(**data_to_location)

    # make the vessel
    data_vessel = {"env": env,                     # The simpy environment 
                "name": "Vessel 01",               # Name of the vessel
                "geometry": geometry_a,            # It is located at the "from location"
                "unloading_func": model.get_unloading_func(1),   # Unloading production is 1 amount / s
                "loading_func": model.get_loading_func(1),     # Loading production is 1 amount / s
                "capacity": 1_000,                 # Capacity of the vessel
                "compute_v": (lambda x: 1)}        # Speed is always 1 m / s

    vessel = TransportProcessingResource(**data_vessel)
    
    # make the activity
    model.Activity(env = env,                   # The simpy environment defined in the first cel
                   name = "Moving amount",      # We are moving soil
                   origin = from_location,      # We originate from the from_site
                   destination = to_location,   # And therefore travel to the to_site
                   loader = vessel,             # The benefit of a TSHD, all steps can be done
                   mover = vessel,              # The benefit of a TSHD, all steps can be done
                   unloader = vessel)           # The benefit of a TSHD, all steps can be done

    # run the activity
    start = env.now
    env.run()

    # Duration of the activity should be equal to loading + sailing + unloading + sailing
    # -- Loading duration is equal to the amount
    # -- Unloading duration is equal to the amount
    # -- Sailing duration is equal to the distance travelled
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_location.geometry)
    dest = shapely.geometry.asShape(to_location.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    np.testing.assert_almost_equal(env.now - start, 20 * 1000 + 20 * distance)


# Delayed starting
def test_start_condition(env, geometry_a, geometry_b, Location, TransportProcessingResource):
    amount = 10_000
    
    # Initialize from site with correct parameters
    data_from_location = {"env": env,                       # The simpy environment
                          "name": "Location A",             # The name of the "from location"
                          "geometry": geometry_a,           # The coordinates of the "from location"
                          "capacity": amount,               # The capacity of the "from location"
                          "level": amount}                  # The actual volume of the "from location"
    data_to_location = {  "env": env,                       # The simpy environment
                          "name": "Location B",             # The name of the "to location"
                          "geometry": geometry_b,           # The coordinates of the "to location"
                          "capacity": amount,               # The capacity of the "to location"
                          "level": 0}                       # The actual volume of the "to location"

    from_location = Location(**data_from_location)
    to_location = Location(**data_to_location)

    # make the vessel
    data_vessel = {"env": env,                     # The simpy environment 
                "name": "Vessel 01",               # Name of the vessel
                "geometry": geometry_a,            # It is located at the "from location"
                "unloading_func": model.get_unloading_func(1),   # Unloading production is 1 amount / s
                "loading_func": model.get_loading_func(1),     # Loading production is 1 amount / s
                "capacity": 1_000,                 # Capacity of the vessel
                "compute_v": (lambda x: 1)}        # Speed is always 1 m / s

    vessel = TransportProcessingResource(**data_vessel)
    
    # TimeCondition - start after 14 days
    delay = env.now + 14 * 7 * 24 * 3600
    time_condition = env.timeout(delay)

    # make the activity
    model.Activity(env = env,                           # The simpy environment defined in the first cel
                   name = "Moving amount",              # We are moving soil
                   origin = from_location,              # We originate from the from_site
                   destination = to_location,           # And therefore travel to the to_site
                   loader = vessel,                     # The benefit of a TSHD, all steps can be done
                   mover = vessel,                      # The benefit of a TSHD, all steps can be done
                   unloader = vessel,                   # The benefit of a TSHD, all steps can be done
                   start_event = time_condition,        # We can start after 14 days
                   stop_event = None)                   # Stop when both conditions are satisfied
    
    # run the activity
    start = env.now
    env.run()

    # Test level of the from_location
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_location.geometry)
    dest = shapely.geometry.asShape(to_location.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    np.testing.assert_almost_equal(env.now - start, delay + 20 * 1000 + 20 * distance)


# Testing the AndCondition
@pytest.mark.skip(reason="no new equivalent of this LevelCondition yet")
def test_and_condition(env, geometry_a, geometry_b, Location, TransportProcessingResource):
    amount = 10_000
    
    # Initialize from site with correct parameters
    data_from_location = {"env": env,                       # The simpy environment
                          "name": "Location A",             # The name of the "from location"
                          "geometry": geometry_a,           # The coordinates of the "from location"
                          "capacity": amount,               # The capacity of the "from location"
                          "level": amount}                  # The actual volume of the "from location"
    data_to_location = {  "env": env,                       # The simpy environment
                          "name": "Location B",             # The name of the "to location"
                          "geometry": geometry_b,           # The coordinates of the "to location"
                          "capacity": amount,               # The capacity of the "to location"
                          "level": 0}                       # The actual volume of the "to location"

    from_location = Location(**data_from_location)
    to_location = Location(**data_to_location)

    # make the vessel
    data_vessel = {"env": env,                     # The simpy environment 
                "name": "Vessel 01",               # Name of the vessel
                "geometry": geometry_a,            # It is located at the "from location"
                "unloading_func": model.get_unloading_func(1),   # Unloading production is 1 amount / s
                "loading_func": model.get_loading_func(1),     # Loading production is 1 amount / s
                "capacity": 1_000,                 # Capacity of the vessel
                "compute_v": (lambda x: 1)}        # Speed is always 1 m / s

    vessel = TransportProcessingResource(**data_vessel)
    
    # LevelCondition - finished after 1 trip
    level_condition = model.LevelCondition(from_location, 0, 9000)

    # TimeCondition - finished after 5 trips
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_location.geometry)
    dest = shapely.geometry.asShape(to_location.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    start = env.now
    end = 10 * 1000 + 10 * distance

    time_condition = model.TimeCondition(env, datetime.datetime.fromtimestamp(start), datetime.datetime.fromtimestamp(start + end))

    # AndCondition - combination of Level and Time
    and_condition = model.AndCondition([level_condition, time_condition])

    # make the activity
    model.Activity(env = env,                       # The simpy environment defined in the first cel
                   name = "Moving amount",          # We are moving soil
                   origin = from_location,          # We originate from the from_site
                   destination = to_location,       # And therefore travel to the to_site
                   loader = vessel,                 # The benefit of a TSHD, all steps can be done
                   mover = vessel,                  # The benefit of a TSHD, all steps can be done
                   unloader = vessel,               # The benefit of a TSHD, all steps can be done
                   start_event = None,          # We can start right away and do not stop
                   stop_event = and_condition)  # Stop when both conditions are satisfied
    
    # run the activity
    start = env.now
    env.run()

    # Test level of the from_location
    assert level_condition.min_level <= from_location.container.level <= level_condition.max_level

    # Test time of the simulation
    assert time.mktime(time_condition.start.timetuple()) <= env.now <= time.mktime(time_condition.stop.timetuple())

def test_sequential_activities(env, geometry_a, geometry_b, Location, TransportProcessingResource):
    """ Test if activities only start after another one is finished. """

    amount = 10_000
    
    # Initialize from site with correct parameters
    data_from_location = {"env": env,                       # The simpy environment
                          "name": "Location A",             # The name of the "from location"
                          "geometry": geometry_a,           # The coordinates of the "from location"
                          "capacity": amount,               # The capacity of the "from location"
                          "level": amount}                  # The actual volume of the "from location"
    data_to_location = {  "env": env,                       # The simpy environment
                          "name": "Location B",             # The name of the "to location"
                          "geometry": geometry_b,           # The coordinates of the "to location"
                          "capacity": amount / 2,           # The capacity of the "to location"
                          "level": 0}                       # The actual volume of the "to location"

    from_location = Location(**data_from_location)
    to_location_1 = Location(**data_to_location)
    to_location_2 = Location(**data_to_location)

    # make the vessel
    data_vessel = {"env": env,                                      # The simpy environment 
                   "name": "Vessel",
                   "geometry": geometry_a,                          # It is located at the "from location"
                   "unloading_func": model.get_unloading_func(1),   # Unloading production is 1 amount / s
                   "loading_func": model.get_loading_func(1),       # Loading production is 1 amount / s
                   "capacity": 1_000,                               # Capacity of the vessel
                   "compute_v": (lambda x: 1)}                      # Speed is always 1 m / s

    vessel_1 = TransportProcessingResource(**data_vessel)
    vessel_2 = TransportProcessingResource(**data_vessel)

    # make the activity
    activity_1 = model.Activity(env = env,                              # The simpy environment defined in the first cel
                                name = "Moving amount",                 # We are moving soil
                                origin = from_location,                 # We originate from the from_site
                                destination = to_location_1,            # And therefore travel to the to_site
                                loader = vessel_1,                      # The benefit of a TSHD, all steps can be done
                                mover = vessel_1,                       # The benefit of a TSHD, all steps can be done
                                unloader = vessel_1,                    # The benefit of a TSHD, all steps can be done
                                start_event = None,                     # We can start right away
                                stop_event = None)                      # Stop when both conditions are satisfied
    activity_2 = model.Activity(env = env,                              # The simpy environment defined in the first cel
                                name = "Moving amount",                 # We are moving soil
                                origin = from_location,                 # We originate from the from_site
                                destination = to_location_2,            # And therefore travel to the to_site
                                loader = vessel_2,                      # The benefit of a TSHD, all steps can be done
                                mover = vessel_2,                       # The benefit of a TSHD, all steps can be done
                                unloader = vessel_2,                    # The benefit of a TSHD, all steps can be done
                                start_event = activity_1.main_process,  # We can start right away
                                stop_event = None)                      # Stop when both conditions are satisfied
    
    # run the activity
    start = env.now
    env.run()

    # Test level of the from_location
    wgs84 = pyproj.Geod(ellps='WGS84')
    orig = shapely.geometry.asShape(from_location.geometry)
    dest = shapely.geometry.asShape(to_location_1.geometry)
    _, _, distance = wgs84.inv(orig.x, orig.y, dest.x, dest.y)

    assert activity_1.log["Timestamp"][-1] == activity_2.log["Timestamp"][0]

    np.testing.assert_almost_equal(env.now - start, 20 * 1000 + 20 * distance)
    np.testing.assert_almost_equal((activity_1.log["Timestamp"][-1] - activity_1.log["Timestamp"][0]).total_seconds(), (20 * 1000 + 20 * distance) / 2)
    np.testing.assert_almost_equal((activity_2.log["Timestamp"][0] - activity_1.log["Timestamp"][0]).total_seconds(), (20 * 1000 + 20 * distance) / 2)
    np.testing.assert_almost_equal((activity_2.log["Timestamp"][-1] - activity_2.log["Timestamp"][0]).total_seconds(), (20 * 1000 + 20 * distance) / 2)