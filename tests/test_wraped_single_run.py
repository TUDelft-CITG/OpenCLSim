"""Test package."""
import datetime

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import parse_log


def test_wraped_single_run():
    """Test wraped single run."""
    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)

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
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,
        ),
        {},
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "geometry": location_from_site,
        "capacity": 5_000,
        "level": 5_000,
    }

    data_to_site = {
        "env": my_env,
        "name": "Dumplocatie",
        "geometry": location_to_site,
        "capacity": 5_000,
        "level": 0,
    }

    from_site = Site(**data_from_site)
    to_site = Site(**data_to_site)

    data_hopper = {
        "env": my_env,
        "name": "Hopper 01",
        "geometry": location_from_site,
        "capacity": 1000,
        "compute_v": lambda x: 10 + 2 * x,
        "loading_rate": 1,
        "unloading_rate": 5,
    }

    hopper = TransportProcessingResource(**data_hopper)

    single_run, activity, while_activity = model.single_run_process(
        name="single_run",
        registry={},
        env=my_env,
        origin=from_site,
        destination=to_site,
        mover=hopper,
        loader=hopper,
        unloader=hopper,
    )

    my_env.run()

    hopper_log = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 16, 40),
            datetime.datetime(1970, 1, 1, 0, 16, 40),
            datetime.datetime(1970, 1, 1, 0, 16, 40),
            datetime.datetime(1970, 1, 1, 0, 29, 45, 687159),
            datetime.datetime(1970, 1, 1, 0, 29, 45, 687159),
            datetime.datetime(1970, 1, 1, 0, 29, 45, 687159),
            datetime.datetime(1970, 1, 1, 0, 33, 5, 687159),
            datetime.datetime(1970, 1, 1, 0, 33, 5, 687159),
            datetime.datetime(1970, 1, 1, 0, 33, 5, 687159),
            datetime.datetime(1970, 1, 1, 0, 48, 48, 511751),
            datetime.datetime(1970, 1, 1, 0, 48, 48, 511751),
            datetime.datetime(1970, 1, 1, 0, 48, 48, 511751),
            datetime.datetime(1970, 1, 1, 1, 5, 28, 511751),
            datetime.datetime(1970, 1, 1, 1, 5, 28, 511751),
            datetime.datetime(1970, 1, 1, 1, 5, 28, 511751),
            datetime.datetime(1970, 1, 1, 1, 18, 34, 198910),
            datetime.datetime(1970, 1, 1, 1, 18, 34, 198910),
            datetime.datetime(1970, 1, 1, 1, 18, 34, 198910),
            datetime.datetime(1970, 1, 1, 1, 21, 54, 198910),
            datetime.datetime(1970, 1, 1, 1, 21, 54, 198910),
            datetime.datetime(1970, 1, 1, 1, 21, 54, 198910),
            datetime.datetime(1970, 1, 1, 1, 37, 37, 23501),
            datetime.datetime(1970, 1, 1, 1, 37, 37, 23501),
            datetime.datetime(1970, 1, 1, 1, 37, 37, 23501),
            datetime.datetime(1970, 1, 1, 1, 54, 17, 23501),
            datetime.datetime(1970, 1, 1, 1, 54, 17, 23501),
            datetime.datetime(1970, 1, 1, 1, 54, 17, 23501),
            datetime.datetime(1970, 1, 1, 2, 7, 22, 710661),
            datetime.datetime(1970, 1, 1, 2, 7, 22, 710661),
            datetime.datetime(1970, 1, 1, 2, 7, 22, 710661),
            datetime.datetime(1970, 1, 1, 2, 10, 42, 710661),
            datetime.datetime(1970, 1, 1, 2, 10, 42, 710661),
            datetime.datetime(1970, 1, 1, 2, 10, 42, 710661),
            datetime.datetime(1970, 1, 1, 2, 26, 25, 535252),
            datetime.datetime(1970, 1, 1, 2, 26, 25, 535252),
            datetime.datetime(1970, 1, 1, 2, 26, 25, 535252),
            datetime.datetime(1970, 1, 1, 2, 43, 5, 535252),
            datetime.datetime(1970, 1, 1, 2, 43, 5, 535252),
            datetime.datetime(1970, 1, 1, 2, 43, 5, 535252),
            datetime.datetime(1970, 1, 1, 2, 56, 11, 222411),
            datetime.datetime(1970, 1, 1, 2, 56, 11, 222411),
            datetime.datetime(1970, 1, 1, 2, 56, 11, 222411),
            datetime.datetime(1970, 1, 1, 2, 59, 31, 222411),
            datetime.datetime(1970, 1, 1, 2, 59, 31, 222411),
            datetime.datetime(1970, 1, 1, 2, 59, 31, 222411),
            datetime.datetime(1970, 1, 1, 3, 15, 14, 47003),
            datetime.datetime(1970, 1, 1, 3, 15, 14, 47003),
            datetime.datetime(1970, 1, 1, 3, 15, 14, 47003),
            datetime.datetime(1970, 1, 1, 3, 31, 54, 47003),
            datetime.datetime(1970, 1, 1, 3, 31, 54, 47003),
            datetime.datetime(1970, 1, 1, 3, 31, 54, 47003),
            datetime.datetime(1970, 1, 1, 3, 44, 59, 734162),
            datetime.datetime(1970, 1, 1, 3, 44, 59, 734162),
            datetime.datetime(1970, 1, 1, 3, 44, 59, 734162),
            datetime.datetime(1970, 1, 1, 3, 48, 19, 734162),
            datetime.datetime(1970, 1, 1, 3, 48, 19, 734162),
        ],
        "ActivityState": [
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
        ],
        "ObjectState": [
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 1000.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
        ],
    }
    from_site_log = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 16, 40),
            datetime.datetime(1970, 1, 1, 0, 48, 48, 511751),
            datetime.datetime(1970, 1, 1, 1, 5, 28, 511751),
            datetime.datetime(1970, 1, 1, 1, 37, 37, 23501),
            datetime.datetime(1970, 1, 1, 1, 54, 17, 23501),
            datetime.datetime(1970, 1, 1, 2, 26, 25, 535252),
            datetime.datetime(1970, 1, 1, 2, 43, 5, 535252),
            datetime.datetime(1970, 1, 1, 3, 15, 14, 47003),
            datetime.datetime(1970, 1, 1, 3, 31, 54, 47003),
        ],
        "ActivityState": [
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
        ],
        "ObjectState": [
            {"container level": 5000, "geometry": (4.18055556, 52.18664444)},
            {"container level": 4000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 4000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 3000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 3000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 2000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 2000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 1000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 1000.0, "geometry": (4.18055556, 52.18664444)},
            {"container level": 0.0, "geometry": (4.18055556, 52.18664444)},
        ],
    }
    to_site_log = {
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 29, 45, 687159),
            datetime.datetime(1970, 1, 1, 0, 33, 5, 687159),
            datetime.datetime(1970, 1, 1, 1, 18, 34, 198910),
            datetime.datetime(1970, 1, 1, 1, 21, 54, 198910),
            datetime.datetime(1970, 1, 1, 2, 7, 22, 710661),
            datetime.datetime(1970, 1, 1, 2, 10, 42, 710661),
            datetime.datetime(1970, 1, 1, 2, 56, 11, 222411),
            datetime.datetime(1970, 1, 1, 2, 59, 31, 222411),
            datetime.datetime(1970, 1, 1, 3, 44, 59, 734162),
            datetime.datetime(1970, 1, 1, 3, 48, 19, 734162),
        ],
        "ActivityState": [
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
        ],
        "ObjectState": [
            {"container level": 0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 1000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 1000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 2000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 2000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 3000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 3000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 4000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 4000.0, "geometry": (4.25222222, 52.11428333)},
            {"container level": 5000.0, "geometry": (4.25222222, 52.11428333)},
        ],
    }

    assert my_env.now == 13699.734162066252

    del hopper.log["ActivityID"]
    del from_site.log["ActivityID"]
    del to_site.log["ActivityID"]

    assert parse_log(hopper.log) == hopper_log
    assert parse_log(from_site.log) == from_site_log
    assert parse_log(to_site.log) == to_site_log
