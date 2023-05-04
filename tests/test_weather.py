"""Test application for the weather plugin."""

import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugin

from .test_utils import assert_log


def test_weather():
    """Test function for weather plugin."""
    simulation_start = datetime.datetime(2009, 1, 1)
    my_env = simpy.Environment(initial_time=simulation_start.timestamp())
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
            core.Identifiable,
            core.Log,
        ),
        {},
    )

    TestMoveActivity = type(
        "TestMoveActivity",
        (
            plugin.HasWeatherPluginActivity,
            model.MoveActivity,  # the order is critical!
        ),
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

    from_site = Site(
        env=my_env,
        name="Winlocatie",
        geometry=location_from_site,
        capacity=120,
        level=120,
    )
    to_site = Site(
        env=my_env,
        name="Dumplocatie",
        geometry=location_to_site,
        capacity=120,
        level=0,
    )
    hopper = TransportProcessingResource(
        env=my_env,
        name="Hopper 01",
        geometry=location_from_site,
        capacity=4,
        compute_v=lambda x: 10,
    )

    parent = Path(__file__).resolve().parent

    metocean_df = pd.read_csv(parent / "data" / "unit_test_weather.csv")
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
        name="sailing_crit",
        condition="Hs [m]",
        maximum=6,
        window_length=3600,
    )

    loading_crit = plugin.WeatherCriterion(
        name="loading_crit",
        condition="Hs [m]",
        maximum=4.5,
        window_length=3600,
    )

    single_run = [
        TestMoveActivity(
            env=my_env,
            name="sailing empty",
            registry=registry,
            mover=hopper,
            destination=from_site,
            metocean_criteria=sailing_crit,
            metocean_df=metocean_df,
        ),
        TestShiftActivity(
            env=my_env,
            name="Loading",
            registry=registry,
            processor=hopper,
            origin=from_site,
            destination=hopper,
            amount=4,
            duration=3600,
            metocean_criteria=loading_crit,
            metocean_df=metocean_df,
        ),
        TestMoveActivity(
            env=my_env,
            name="sailing full",
            registry=registry,
            mover=hopper,
            destination=to_site,
            metocean_criteria=sailing_crit,
            metocean_df=metocean_df,
        ),
        TestShiftActivity(
            env=my_env,
            name="unloading",
            registry=registry,
            processor=hopper,
            origin=hopper,
            destination=to_site,
            amount=4,
            duration=3600,
            metocean_criteria=loading_crit,
            metocean_df=metocean_df,
        ),
    ]

    activity = model.SequentialActivity(
        env=my_env,
        name="Single run process",
        id="6dbbbdf7-4589-11e9-bf3b-b469212bff60",
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

    assert my_env.now == 1262737885.6491823

    assert_log(hopper)
    assert_log(while_activity)
