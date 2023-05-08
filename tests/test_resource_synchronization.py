"""Test package."""

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_test_resource_synchronization():
    """Test resource Synchronization."""

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
        id="6dbbbdf4-4589-11e9-a501-b469212bff5d",
        geometry=location_from_site,
        capacity=10,
        level=8,
    )

    hopper1 = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        id="6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        capacity=4,
        compute_v=lambda x: 10,
    )

    hopper2 = TransportProcessingResource(
        env=my_env,
        name="Hopper 02",
        id="5dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        capacity=4,
        compute_v=lambda x: 10,
    )

    requested_resources1 = {}
    activity1 = model.ShiftAmountActivity(
        env=my_env,
        name="Transfer1",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff52",
        registry=registry,
        processor=hopper1,
        origin=from_site,
        destination=hopper1,
        amount=1,
        duration=20,
        requested_resources=requested_resources1,
    )

    seq_activity1 = model.SequentialActivity(
        env=my_env,
        name="Sequential process1",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff60",
        registry=registry,
        sub_processes=[activity1],
        requested_resources=requested_resources1,
    )

    while1 = model.WhileActivity(
        env=my_env,
        name="while1",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        registry=registry,
        sub_processes=[seq_activity1],
        requested_resources=requested_resources1,
        condition_event=[
            {
                "or": [
                    {"type": "container", "concept": hopper1, "state": "full"},
                    {"type": "container", "concept": from_site, "state": "empty"},
                ]
            }
        ],
    )

    activity2 = model.ShiftAmountActivity(
        env=my_env,
        name="Transfer2",
        id="5dbbbdf7-4589-11e9-bf3b-b469212bff52",
        registry=registry,
        processor=hopper2,
        origin=from_site,
        destination=hopper2,
        amount=1,
        duration=20,
    )

    seq_activity2 = model.SequentialActivity(
        env=my_env,
        name="Sequential process2",
        id="5dbbbdf7-4589-11e9-bf3b-b469212bff60",
        registry=registry,
        sub_processes=[activity2],
    )
    while2 = model.WhileActivity(
        env=my_env,
        name="while2",
        id="5dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        registry=registry,
        sub_processes=[seq_activity2],
        condition_event=[
            {
                "or": [
                    {"type": "container", "concept": hopper2, "state": "full"},
                    {"type": "container", "concept": from_site, "state": "empty"},
                ]
            }
        ],
    )

    model.register_processes([while1, while2])
    my_env.run()

    assert my_env.now == 160
    assert_log(from_site)
    assert_log(while1)
    assert_log(while2)
