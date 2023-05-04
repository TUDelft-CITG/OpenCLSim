"""Test package."""

import pytest
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_move_activity():
    """Test the move acitity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)

    Site = type(
        "Site",
        (
            core.Identifiable,
            core.Log,
            core.Locatable,
            core.HasContainer,
            core.HasResource,
        ),
        {},
    )
    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.ContainerDependentMovable,
            core.HasResource,
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.Identifiable,
            core.Log,
        ),
        {},
    )

    to_site = Site(
        env=my_env,
        name="Dumplocatie",
        id="6dbbbdf5-4589-11e9-82b2-b469212bff5b",
        geometry=location_to_site,
        capacity=10,
        level=0,
    )
    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        id="6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        capacity=5,
        compute_v=lambda x: 10,
    )

    activity = model.MoveActivity(
        env=my_env,
        name="Soil movement",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        registry=registry,
        mover=hopper,
        destination=to_site,
    )
    model.register_processes([activity])
    my_env.run()

    assert my_env.now == pytest.approx(942.8245912734186)
    assert_log(activity)
    assert_log(hopper)
    assert_log(to_site)
