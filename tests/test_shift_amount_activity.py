"""Test package."""

import datetime

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import parse_log


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

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "geometry": location_from_site,
        "capacity": 10,
        "level": 2,
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

    data_hopper = {
        "env": my_env,
        "name": "Hopper 01",
        "geometry": location_from_site,
        "loading_rate": 1,
        "unloading_rate": 1,
        "capacity": 5,
        "compute_v": compute_v_provider(5, 4.5),
    }

    hopper = TransportProcessingResource(**data_hopper)

    shift_amount_activity_data = {
        "env": my_env,
        "name": "Transfer MP",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        "registry": registry,
        "processor": hopper,
        "origin": from_site,
        "destination": hopper,
        "amount": 100,
        "duration": 10,
    }
    activity = model.ShiftAmountActivity(**shift_amount_activity_data)

    my_env.run()

    activity_benchmark = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        ],
        "ActivityState": ["START", "STOP"],
        "ObjectState": [{}, {}],
    }

    hopper_benchmark = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        ],
        "ActivityState": ["START", "START", "STOP", "STOP"],
        "ObjectState": [
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 2.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 2.0},
        ],
    }

    site_benchmark = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        ],
        "ActivityState": ["START", "STOP"],
        "ObjectState": [
            {"container level": 2, "geometry": (4.18055556, 52.18664444)},
            {"container level": 0, "geometry": (4.18055556, 52.18664444)},
        ],
    }

    assert my_env.now == 10
    assert parse_log(from_site.log) == site_benchmark
    assert parse_log(hopper.log) == hopper_benchmark
    assert parse_log(activity.log) == activity_benchmark
