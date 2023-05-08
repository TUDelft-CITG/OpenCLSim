"""Test package."""

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_mulitcontainer():
    """Test the multicontainer."""
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    Site = type(
        "Site",
        (
            core.Identifiable,
            core.Log,
            core.Locatable,
            core.HasMultiContainer,
            core.HasResource,
        ),
        {},
    )

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.MultiContainerDependentMovable,
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
        id="6dbbbdf4-4589-11e9-a501-b469212bff5d",
        geometry=location_from_site,
        store_capacity=4,
        initials=[
            {"id": "MP", "level": 2, "capacity": 10},
            {"id": "TP", "level": 0, "capacity": 2},
        ],
    )

    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        id="6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        store_capacity=4,
        compute_v=lambda x: 10,
        initials=[
            {"id": "MP", "level": 0, "capacity": 2},
            {"id": "TP", "level": 0, "capacity": 2},
        ],
    )

    activity = model.ShiftAmountActivity(
        env=my_env,
        name="Transfer MP",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff52",
        registry=registry,
        processor=hopper,
        origin=from_site,
        destination=hopper,
        amount=1,
        id_="MP",
        duration=20,
    )

    model.register_processes([activity])
    my_env.run()

    assert my_env.now == 20
    assert hopper.container.get_level(id_="MP") == 1
    assert hopper.container.get_level(id_="TP") == 0
    assert from_site.container.get_level(id_="TP") == 0
    assert from_site.container.get_level(id_="MP") == 1

    assert_log(hopper)
    assert_log(activity)
    assert_log(from_site)
