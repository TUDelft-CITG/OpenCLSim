"""Test application for the weather plugin."""

import datetime

import pandas as pd
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugin

from .test_utils import parse_log


def test_weather():
    """Test function for weather plugin."""
    # setup environment
    simulation_start = datetime.datetime(2009, 1, 1)
    my_env = simpy.Environment(initial_time=simulation_start.timestamp())
    registry = {}

    import numpy as np

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
            core.HasResource,
        ),
        {},
    )

    TestMoveActivity = type(
        "TestMoveActivity",
        (plugin.HasWeatherPluginActivity, model.MoveActivity),  # the order is critical!
        {},
    )

    TestShiftActivity = type(
        "TestShiftActivity",
        (
            plugin.HasWeatherPluginActivity,
            model.ShiftAmountActivity,  # the order is critical!
        ),
        {},
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "geometry": location_from_site,
        "capacity": 12,
        "level": 12,
    }

    data_to_site = {
        "env": my_env,
        "name": "Dumplocatie",
        "geometry": location_to_site,
        "capacity": 12,
        "level": 0,
    }

    from_site = Site(**data_from_site)
    to_site = Site(**data_to_site)

    data_hopper = {
        "env": my_env,
        "name": "Hopper 01",
        "geometry": location_from_site,
        "capacity": 4,
        "compute_v": lambda x: 10,
    }

    hopper = TransportProcessingResource(**data_hopper)

    metocean_df = pd.read_csv("./tests/data/unit_test_weather.csv")
    metocean_df = metocean_df.set_index(
        pd.to_datetime(metocean_df["Time"], dayfirst=True)
    )
    metocean_df = metocean_df.sort_index()

    metocean_df["Hs [m]"] = (
        4
        + 1.5 * np.sin(metocean_df["  Hour"] / 24 * 8 * np.pi)
        + 1.5 * np.sin(metocean_df["  Hour"] / 24 * 6 * np.pi)
    )

    metocean_df = metocean_df.set_index(
        pd.to_datetime(metocean_df["Time"], dayfirst=True)
    )
    metocean_df = metocean_df.sort_index()
    metocean_df["ts"] = metocean_df.index.values.astype(float) / 1_000_000_000

    sailing_crit = plugin.WeatherCriterion(
        **{
            "name": "sailing_crit",
            "condition": "Hs [m]",
            "maximum": 6,
            "window_length": 3600,
        }
    )

    loading_crit = plugin.WeatherCriterion(
        **{
            "name": "loading_crit",
            "condition": "Hs [m]",
            "maximum": 4.5,
            "window_length": 3600,
        }
    )

    single_run = [
        TestMoveActivity(
            **{
                "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
                "env": my_env,
                "name": "Soil movement",
                "registry": registry,
                "mover": hopper,
                "destination": from_site,
                "metocean_criteria": sailing_crit,
                "metocean_df": metocean_df,
                "postpone_start": True,
            }
        ),
        TestShiftActivity(
            **{
                "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
                "env": my_env,
                "name": "Transfer MP",
                "registry": registry,
                "processor": hopper,
                "origin": from_site,
                "destination": hopper,
                "amount": 4,
                "duration": 3600,
                "postpone_start": True,
                "metocean_criteria": loading_crit,
                "metocean_df": metocean_df,
            }
        ),
        TestMoveActivity(
            **{
                "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
                "env": my_env,
                "name": "Soil movement",
                "registry": registry,
                "mover": hopper,
                "destination": to_site,
                "metocean_criteria": sailing_crit,
                "metocean_df": metocean_df,
                "postpone_start": True,
            }
        ),
        TestShiftActivity(
            **{
                "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
                "env": my_env,
                "name": "Transfer TP",
                "registry": registry,
                "processor": hopper,
                "origin": hopper,
                "destination": to_site,
                "amount": 4,
                "duration": 3600,
                "postpone_start": True,
                "metocean_criteria": loading_crit,
                "metocean_df": metocean_df,
            }
        ),
    ]

    activity = model.SequentialActivity(
        **{
            "env": my_env,
            "name": "Single run process",
            "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
            "registry": registry,
            "sub_processes": single_run,
            "postpone_start": True,
        }
    )

    expr = [{"type": "container", "concept": to_site, "state": "full"}]
    while_data = {
        "env": my_env,
        "name": "while",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff61",
        "registry": registry,
        "sub_process": activity,
        "condition_event": expr,
        "postpone_start": False,
    }
    model.WhileActivity(**while_data)

    my_env.run()

    hopper_benchmark = {
        "Timestamp": [
            datetime.datetime(2010, 1, 1, 3, 0),
            datetime.datetime(2010, 1, 1, 3, 0),
            datetime.datetime(2010, 1, 1, 4, 0),
            datetime.datetime(2010, 1, 1, 4, 0),
            datetime.datetime(2010, 1, 1, 5, 0),
            datetime.datetime(2010, 1, 1, 5, 0),
            datetime.datetime(2010, 1, 1, 5, 0),
            datetime.datetime(2010, 1, 1, 5, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 5, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 5, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 6, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 6, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 6, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 6, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 6, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 6, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 7, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 7, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 7, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 7, 47, 8, 473773),
            datetime.datetime(2010, 1, 1, 10, 0),
            datetime.datetime(2010, 1, 1, 10, 0),
            datetime.datetime(2010, 1, 1, 11, 0),
            datetime.datetime(2010, 1, 1, 11, 0),
            datetime.datetime(2010, 1, 1, 11, 0),
            datetime.datetime(2010, 1, 1, 11, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 11, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 11, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 12, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 12, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 12, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 12, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 12, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 12, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 13, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 13, 31, 25, 649182),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff64",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff63",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff62",
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
        ],
        "ObjectState": [
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 0.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.18055556, 52.18664444), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 4.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
            {"geometry": (4.25222222, 52.11428333), "container level": 0.0},
        ],
    }
    activity_benchmark = {
        "Timestamp": [
            datetime.datetime(2009, 1, 1, 0, 0),
            datetime.datetime(2010, 1, 1, 3, 0),
            datetime.datetime(2010, 1, 1, 3, 0),
            datetime.datetime(2010, 1, 1, 3, 0),
            datetime.datetime(2010, 1, 1, 6, 15, 42, 824591),
            datetime.datetime(2010, 1, 1, 6, 31, 25, 649182),
            datetime.datetime(2010, 1, 1, 11, 0),
            datetime.datetime(2010, 1, 1, 11, 15, 42, 824591),
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff65",
        ],
        "ActivityState": [
            "WAIT_START",
            "WAIT_STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
        ],
        "ObjectState": [
            {
                "message": "move activity Soil movement of Hopper 01 to Winlocatie waiting on weather"
            },
            {
                "message": "move activity Soil movement of Hopper 01 to Winlocatie waiting on weather"
            },
            {},
            {},
            {},
            {},
            {},
            {},
        ],
    }

    assert my_env.now == 1262352685.6491823
    assert parse_log(hopper.log) == hopper_benchmark
    assert parse_log(single_run[0].log) == activity_benchmark
