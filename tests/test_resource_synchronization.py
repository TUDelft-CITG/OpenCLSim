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

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5d",
        "geometry": location_from_site,
        "capacity": 10,
        "level": 8,
    }

    from_site = Site(**data_from_site)

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.HasResource,
            core.LoadingFunction,
            core.UnloadingFunction,
        ),
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: 10

    data_hopper1 = {
        "env": my_env,
        "name": "Hopper 01",
        "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        "geometry": location_from_site,
        "loading_rate": 1,
        "unloading_rate": 1,
        "capacity": 4,
        "compute_v": compute_v_provider(5, 4.5),
    }

    hopper1 = TransportProcessingResource(**data_hopper1)

    data_hopper2 = {
        "env": my_env,
        "name": "Hopper 02",
        "ID": "5dbbbdf6-4589-11e9-95a2-b469212bff5b",
        "geometry": location_from_site,
        "loading_rate": 1,
        "unloading_rate": 1,
        "capacity": 4,
        "compute_v": compute_v_provider(5, 4.5),
    }
    hopper2 = TransportProcessingResource(**data_hopper2)

    requested_resources1 = {}
    shift_amount_activity_loading_data1 = {
        "env": my_env,
        "name": "Transfer1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
        "registry": registry,
        "processor": hopper1,
        "origin": from_site,
        "destination": hopper1,
        "amount": 1,
        "duration": 20,
        "requested_resources": requested_resources1,
    }
    activity1 = model.ShiftAmountActivity(**shift_amount_activity_loading_data1)

    sequential_activity_data1 = {
        "env": my_env,
        "name": "Sequential process1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
        "registry": registry,
        "sub_processes": [activity1],
        "requested_resources": requested_resources1,
    }
    seq_activity1 = model.SequentialActivity(**sequential_activity_data1)

    while_data1 = {
        "env": my_env,
        "name": "while1",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        "registry": registry,
        "sub_processes": [seq_activity1],
        "condition_event": [
            {
                "or": [
                    {"type": "container", "concept": hopper1, "state": "full"},
                    {"type": "container", "concept": from_site, "state": "empty"},
                ]
            }
        ],
        "requested_resources": requested_resources1,
    }
    model.WhileActivity(**while_data1)

    shift_amount_activity_loading_data2 = {
        "env": my_env,
        "name": "Transfer2",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff52",
        "registry": registry,
        "processor": hopper2,
        "origin": from_site,
        "destination": hopper2,
        "amount": 1,
        "duration": 20,
    }
    activity2 = model.ShiftAmountActivity(**shift_amount_activity_loading_data2)

    sequential_activity_data2 = {
        "env": my_env,
        "name": "Sequential process2",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff60",
        "registry": registry,
        "sub_processes": [activity2],
    }
    seq_activity2 = model.SequentialActivity(**sequential_activity_data2)

    while_data2 = {
        "env": my_env,
        "name": "while2",
        "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        "registry": registry,
        "sub_processes": [seq_activity2],
        "condition_event": [
            {
                "or": [
                    {"type": "container", "concept": hopper2, "state": "full"},
                    {"type": "container", "concept": from_site, "state": "empty"},
                ]
            }
        ],
    }
    model.WhileActivity(**while_data2)

    my_env.run()

    assert my_env.now == 160
    assert_log(from_site.log)
