#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `openclsim` package."""

import pytest
import simpy
import shapely.geometry
import pyproj
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

            graph.add_edge((x_1, y_1), (x_2, y_2), maxSpeed=5)

    return graph


# The environment
@pytest.fixture
def env(FG):
    env = simpy.Environment()
    env.FG = FG

    return env


def test_moving_over_path(locatable_a, locatable_b, locatable_c, env):
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
    distance = 0
    distance += mover.wgs84.inv(
        locatable_a.geometry.x,
        locatable_a.geometry.y,
        locatable_b.geometry.x,
        locatable_b.geometry.y,
    )[2]
    distance += mover.wgs84.inv(
        locatable_b.geometry.x,
        locatable_b.geometry.y,
        locatable_c.geometry.x,
        locatable_c.geometry.y,
    )[2]

    assert env.now == distance
