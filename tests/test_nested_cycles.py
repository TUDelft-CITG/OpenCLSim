"""Test package."""

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_nested_cycles():
    """Test nested cycles."""

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
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)

    from_site = Site(
        env=my_env,
        name="Winlocatie",
        id="6dbbbdf4-4589-11e9-a501-b469212bff5d",
        geometry=location_from_site,
        capacity=100,
        level=50,
    )

    to_site = Site(
        env=my_env,
        name="Dumplocatie",
        id="6dbbbdf5-4589-11e9-82b2-b469212bff5c",
        geometry=location_to_site,
        capacity=50,
        level=0,
    )

    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        id="6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=0.00001,
        unloading_rate=0.00001,
        capacity=5,
        compute_v=lambda x: 10,
    )

    loading_subcycle_processes = [
        model.BasicActivity(
            env=my_env,
            name="loading activity 1",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name="Transfer MP",
            registry=registry,
            processor=hopper,
            origin=from_site,
            destination=hopper,
            amount=1,
            duration=1000,
        ),
        model.BasicActivity(
            env=my_env,
            name="loading activity 2",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
    ]

    loading_subcycle_process = model.RepeatActivity(
        env=my_env,
        name="while_loading_subcycle",
        registry=registry,
        sub_processes=[
            model.SequentialActivity(
                env=my_env,
                name="Loading subcycle",
                registry=registry,
                sub_processes=loading_subcycle_processes,
            )
        ],
        repetitions=5,
    )

    unloading_subcycle_processes = [
        model.BasicActivity(
            env=my_env,
            name="unloading activity 1",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name="Transfer TP",
            registry=registry,
            processor=hopper,
            origin=hopper,
            destination=to_site,
            amount=1,
            duration=1000,
        ),
        model.BasicActivity(
            env=my_env,
            name="unloading activity 2",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
    ]

    unloading_subcycle_process = model.RepeatActivity(
        env=my_env,
        name="while_unloading_subcycle",
        registry=registry,
        sub_processes=[
            model.SequentialActivity(
                env=my_env,
                name="unloading subcycle",
                registry=registry,
                sub_processes=unloading_subcycle_processes,
            )
        ],
        repetitions=5,
    )

    single_run = [
        model.BasicActivity(
            env=my_env,
            name="Basic activity 3",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
        model.MoveActivity(
            env=my_env,
            name="sailing empty",
            registry=registry,
            mover=hopper,
            destination=from_site,
            duration=500,
        ),
        loading_subcycle_process,
        model.MoveActivity(
            env=my_env,
            name="sailing filled",
            registry=registry,
            mover=hopper,
            duration=500,
            destination=to_site,
        ),
        unloading_subcycle_process,
        model.BasicActivity(
            env=my_env,
            name="Basic activity",
            registry=registry,
            duration=100,
            additional_logs=[hopper],
        ),
    ]

    activity = model.SequentialActivity(
        env=my_env,
        name="Single run process",
        registry=registry,
        sub_processes=single_run,
    )

    while_activity = model.WhileActivity(
        env=my_env,
        name="while",
        registry=registry,
        sub_processes=[activity],
        condition_event=[{"type": "container", "concept": to_site, "state": "full"}],
    )

    model.register_processes([while_activity])
    my_env.run()

    assert my_env.now == 132000
    assert_log(while_activity)
