"""Test package."""

import pytest
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugins

from .test_utils import assert_log


def test_delay_plugin():
    """Test the delay plugin."""
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

    DelaySequenceActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.SequentialActivity), {}
    )

    DelayWhileActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.WhileActivity), {}
    )

    DelayMoveActivity = type(
        "TestMoveActivity", (plugins.HasDelayPlugin, model.MoveActivity), {}
    )

    DelayShiftActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.ShiftAmountActivity), {}
    )

    DelayBasicActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.BasicActivity), {}
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)

    from_site = Site(
        env=my_env,
        name="Winlocatie",
        id="6dbbbdf4-4589-11e9-a501-b469212bff5d",
        geometry=location_from_site,
        capacity=12,
        level=12,
    )
    to_site = Site(
        env=my_env,
        name="Dumplocatie",
        id="6dbbbdf5-4589-11e9-82b2-b469212bff5c",
        geometry=location_to_site,
        capacity=12,
        level=0,
    )

    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        id="6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        geometry=location_from_site,
        loading_rate=1,
        unloading_rate=1,
        capacity=4,
        compute_v=lambda x: 10,
    )

    single_run = [
        DelayMoveActivity(
            env=my_env,
            name="sailing empty",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            registry=registry,
            mover=hopper,
            destination=from_site,
            delay_percentage=10,
        ),
        DelayShiftActivity(
            env=my_env,
            name="Transfer MP",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            registry=registry,
            processor=hopper,
            origin=from_site,
            destination=hopper,
            amount=4,
            duration=10,
            delay_percentage=10,
        ),
        DelayMoveActivity(
            env=my_env,
            name="sailing filler",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            registry=registry,
            mover=hopper,
            destination=to_site,
            delay_percentage=10,
        ),
        DelayShiftActivity(
            env=my_env,
            name="Transfer TP",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            registry=registry,
            processor=hopper,
            origin=hopper,
            destination=to_site,
            amount=4,
            duration=10,
            delay_percentage=10,
        ),
        DelayBasicActivity(
            env=my_env,
            name="Basic activity",
            id="6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            registry=registry,
            duration=0,
            additional_logs=[hopper],
            delay_percentage=10,
        ),
    ]
    activity = DelaySequenceActivity(
        env=my_env,
        name="Single run process",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff60",
        registry=registry,
        sub_processes=single_run,
        delay_percentage=10,
    )
    while_activity = DelayWhileActivity(
        env=my_env,
        name="while",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        registry=registry,
        sub_processes=[activity],
        condition_event=[{"type": "container", "concept": to_site, "state": "full"}],
        delay_percentage=10,
    )
    model.register_processes([while_activity])
    my_env.run()

    assert my_env.now == pytest.approx(6354.357654924601)
    assert_log(while_activity)
    assert_log(hopper)
    assert_log(from_site)
    assert_log(to_site)
