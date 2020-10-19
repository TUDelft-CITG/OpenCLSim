"""Test package."""

import datetime

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import parse_log


def test_move_activity():
    """Test the move acitity."""

    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

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

    data_to_site = {
        "env": my_env,
        "name": "Dumplocatie",
        "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5b",
        "geometry": location_to_site,
        "capacity": 10,
        "level": 0,
    }

    to_site = Site(**data_to_site)

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.HasResource,
            core.Processor,
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
        "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        "geometry": location_from_site,
        "loading_rate": 1,
        "unloading_rate": 1,
        "capacity": 5,
        "compute_v": compute_v_provider(5, 4.5),
    }

    hopper = TransportProcessingResource(**data_hopper)

    move_activity_data = {
        "env": my_env,
        "name": "Soil movement",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        "registry": registry,
        "mover": hopper,
        "destination": to_site,
    }
    activity = model.MoveActivity(**move_activity_data)

    my_env.run()

    hopper_benchmark = {
        "Message": [
            "move activity Soil movement of Hopper 01 to Dumplocatie",
            "move activity Soil movement of Hopper 01 to Dumplocatie",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 15, 42, 824591),
        ],
        "Value": [0.0, 0.0],
        "Geometry": [(4.18055556, 52.18664444), (4.25222222, 52.11428333)],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        ],
        "ActivityState": ["START", "STOP"],
    }
    activity_benchmark = {
        "Message": [
            "move activity Soil movement of Hopper 01 to Dumplocatie",
            "move activity Soil movement of Hopper 01 to Dumplocatie",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 15, 42, 824591),
        ],
        "Value": [-1, -1],
        "Geometry": [(4.18055556, 52.18664444), (4.25222222, 52.11428333)],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        ],
        "ActivityState": ["START", "STOP"],
    }
    assert parse_log(hopper.log) == hopper_benchmark
    assert parse_log(activity.log) == activity_benchmark