"""Test package."""

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_shift_amount():
    """Test the shift amount activity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

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
            core.Processor,
            core.HasResource,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.Identifiable,
            core.Log,
        ),
        {},
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    from_site = Site(
        env=my_env,
        name="Winlocatie",
        geometry=location_from_site,
        capacity=10,
        level=2,
    )

    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        capacity=5,
        compute_v=lambda x: 10,
    )

    activity = model.ShiftAmountActivity(
        env=my_env,
        name="Transfer MP",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        registry=registry,
        processor=hopper,
        origin=from_site,
        destination=hopper,
        amount=100,
        duration=10,
    )

    model.register_processes([activity])
    my_env.run()

    assert my_env.now == 10
    assert_log(from_site)
    assert_log(hopper)
    assert_log(activity)
