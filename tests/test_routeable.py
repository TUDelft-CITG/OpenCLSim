#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `openclsim` package."""

import pytest
import simpy
import shapely.geometry
import pyproj
import pandas as pd
import networkx as nx

from openclsim import core

# The various geometries
@pytest.fixture
def geometry_a():
    return shapely.geometry.Point(0, 0)


@pytest.fixture
def geometry_b():
    return shapely.geometry.Point(0, 1)


@pytest.fixture
def geometry_c():
    return shapely.geometry.Point(1, 1)


# The locatables to have a destination when moving
@pytest.fixture
def locatable_a(geometry_a):
    return core.Locatable(geometry_a)


@pytest.fixture
def locatable_b(geometry_b):
    return core.Locatable(geometry_b)


@pytest.fixture
def locatable_c(geometry_c):
    return core.Locatable(geometry_c)


# Create the graph
@pytest.fixture
def FG(geometry_a, geometry_b, geometry_c):
    graph = nx.DiGraph()
    nodes = [geometry_a, geometry_b, geometry_c]

    for node in nodes:
        x = node.x
        y = node.y

        graph.add_node((x, y), geometry=node, name="({}, {})".format(str(x), str(y)))

    # From geometry A to geometry C, through geometry B
    for i, node in enumerate(nodes):

        if i != len(nodes) - 1:
            x_1 = nodes[i].x
            y_1 = nodes[i].y
            x_2 = nodes[i + 1].x
            y_2 = nodes[i + 1].y

            graph.add_edge((x_1, y_1), (x_2, y_2))

    # From geometry C to geometry A, through geometry B
    nodes.reverse()
    for i, node in enumerate(nodes):

        if i != len(nodes) - 1:
            x_1 = nodes[i].x
            y_1 = nodes[i].y
            x_2 = nodes[i + 1].x
            y_2 = nodes[i + 1].y

            graph.add_edge((x_1, y_1), (x_2, y_2), maxSpeed=0.5)

    return graph


# Length of the path
@pytest.fixture
def distance(geometry_a, geometry_b, geometry_c, locatable_a):
    ab = locatable_a.wgs84.inv(geometry_a.x, geometry_a.y, geometry_b.x, geometry_b.y)[
        2
    ]
    bc = locatable_a.wgs84.inv(geometry_b.x, geometry_b.y, geometry_c.x, geometry_c.y)[
        2
    ]

    return ab + bc


# The environment
@pytest.fixture
def env(FG):
    env = simpy.Environment()
    env.FG = FG

    return env


def test_moving_over_path(locatable_a, locatable_c, distance, env):
    """ 
    test if a mover follows a certain path 
    
    sailing speed is 1 m/s, so duration of the event should be the length of the path
    """

    # Create mover class
    class routeable(core.Routeable, core.Log):
        pass

    mover = routeable(env=env, geometry=locatable_a.geometry, v=1)
    mover.ActivityID = "Test activity"

    # Move the mover to geometry c
    env.process(mover.move(locatable_c))
    env.run()

    # Assert mover is at geometry c
    assert mover.geometry.equals(locatable_c.geometry)

    # Assert duration of sailing equals the path
    assert env.now == distance


def test_moving_over_path_maxspeed(locatable_a, locatable_c, distance, env):
    """ 
    test if a mover follows a certain path 
    
    maximum sailing speed is 0.5 m/s, so duration of the event should be twice the length of the path
    """

    # Create mover class
    class routeable(core.Routeable, core.Log):
        pass

    mover = routeable(env=env, geometry=locatable_c.geometry, v=1)
    mover.ActivityID = "Test activity"

    # Move the mover to geometry c
    env.process(mover.move(locatable_a))
    env.run()

    # Assert mover is at geometry c
    assert mover.geometry.equals(locatable_a.geometry)

    # Assert duration of sailing equals the path
    assert env.now == distance * 2


def test_moving_over_path_energy(locatable_a, locatable_c, distance, env):
    """ 
    test if a mover follows a certain path 

    energy use is 2 kwh per second
    from a to c, maximum speed is 1.0 m/s, so energy use is 2 * distance
    from c to a, maximum speed is 0.5 m/s, so energy use is 4 * distance
    """

    # Create mover class
    class routeable(core.Routeable, core.Log, core.EnergyUse):
        pass

    # Energy use
    def energy_use_sailing():
        return lambda x, y: (x / y) * 4

    mover = routeable(
        env=env,
        geometry=locatable_a.geometry,
        v=1,
        energy_use_sailing=energy_use_sailing(),
    )
    mover.ActivityID = "Test activity"

    # Move the mover to geometry c
    env.process(mover.move(locatable_c))
    env.run()

    # Assert energy use
    log = pd.DataFrame.from_dict(mover.log)
    energy_use = 0

    for i in log.index:
        if "Energy" in log.loc[i]["Message"]:
            energy_use += log.loc[i]["Value"]

    assert energy_use == distance * 4

    # Move the mover to geometry a
    env.process(mover.move(locatable_a))
    env.run()

    # Assert energy use
    log = pd.DataFrame.from_dict(mover.log)
    energy_use = 0

    for i in log.index:
        if "Energy" in log.loc[i]["Message"]:
            energy_use += log.loc[i]["Value"]

    assert energy_use == distance * 4 + distance * 8
