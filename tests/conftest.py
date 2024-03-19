"""
Fixtures for the test-suite.
"""

import numpy as np
import pandas as pd
import pytest
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugin
from openclsim.critical_path.dependencies_from_simpy_step import CriticalPathEnvironment


@pytest.fixture()
def simulation_2_barges():
    """
    Fixture returns the simpy.Environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(nr_barges=2, total_amount=100)


@pytest.fixture()
def simulation_2_barges_storm():
    """
    Fixture returns the simpy.Environment, objects and activities
    after a 2-barges simulation with weather delay.
    """
    return demo_data(nr_barges=2, total_amount=100, max_wave=4)


@pytest.fixture()
def simulation_2_barges_start():
    """
    Fixture returns the simpy.Environment, objects and activities
    after a 2-barges simulation with start event (delay).
    """
    return demo_data(nr_barges=2, total_amount=100, start_delay=3600)


@pytest.fixture()
def simulation_2_barges_custom_env():
    """
    Fixture returns the custom environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(nr_barges=2, total_amount=100, env=CriticalPathEnvironment)


@pytest.fixture()
def simulation_2_barges_custom_env_storm():
    """
    Fixture returns the custom environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(
        nr_barges=2, total_amount=100, env=CriticalPathEnvironment, max_wave=4
    )


@pytest.fixture()
def simulation_2_barges_custom_env_start():
    """
    Fixture returns the custom environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(
        nr_barges=2, total_amount=100, env=CriticalPathEnvironment, start_delay=3600
    )


@pytest.fixture()
def simulation_while_sequential():
    """
    Fixture returns the custom environment, objects and activities
    after a simple while-sequential simulation.
    """
    return demo_data_simple(env=CriticalPathEnvironment)


@pytest.fixture()
def simulation_4_barges():
    """
    Fixture returns the simpy.Environment, objects and activities after a 4-barges simulation.
    """
    return demo_data(nr_barges=4, total_amount=100)


def get_sailing_empty(my_env, vessels, i, registry, from_site, duration, max_wave):
    """possible use plugin"""
    if max_wave is not None:
        # create a TestMoveActivity object based on desired mixin classes
        WeatherMoveActivity = type(
            "TestMoveActivity",
            (
                plugin.HasWeatherPluginActivity,
                model.MoveActivity,  # the order is critical!
            ),
            {},
        )

        # generate weather data
        waves_df = pd.DataFrame(
            {
                "Hs [m]": [
                    3.1
                    + 1.5 * np.sin(t / 7200 * np.pi)
                    + 1.5 * np.sin(t / 4000 * np.pi)
                    for t in np.arange(0, 4 * 24 * 3600)
                ],
                "ts": np.arange(0, 4 * 24 * 3600),
            }
        )

        # generate a weather criterion for the sailing process
        sailing_crit = plugin.WeatherCriterion(
            name="sailing_crit",
            condition="Hs [m]",
            maximum=max_wave,
            window_length=900,
        )
        activity = WeatherMoveActivity(
            env=my_env,
            name="sailing empty:" + vessels[f"vessel{i}"].name,
            registry=registry,
            mover=vessels[f"vessel{i}"],
            destination=from_site,
            duration=duration,
            metocean_criteria=sailing_crit,
            metocean_df=waves_df,
        )
    else:
        activity = model.MoveActivity(
            env=my_env,
            name="sailing empty:" + vessels[f"vessel{i}"].name,
            registry=registry,
            mover=vessels[f"vessel{i}"],
            destination=from_site,
            duration=duration,
        )
    return activity


def demo_data(nr_barges, total_amount, env=None, max_wave=None, start_delay=0):
    """
    Run a simulation where <nr_barges> barges need to shift an amount of <total_amount>
    from site 1 to site 2 whereafter a larger vessel can come into action.

    Parameters
    ----------
    nr_barges : int
        Number of barges in the simulation.
    total_amount : int
        Total amount to be transported in the simulation.
    env : simpy.Environment or class that inherits from simpy.Environment
        Optional. If None, default to simpy Environment
    """
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

    simulation_start = 0
    if env is None:
        my_env = simpy.Environment(initial_time=simulation_start)
    else:
        my_env = env(initial_time=simulation_start)

    registry = {}

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": 2 * total_amount,
        "level": 2 * total_amount,
        "nr_resources": 1,
    }
    from_site = Site(**data_from_site)

    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {
        "env": my_env,
        "name": "to_site",
        "geometry": location_to_site,
        "capacity": total_amount,
        "level": 0,
        "nr_resources": 4,
    }
    to_site = Site(**data_to_site)

    location_to_site2 = shapely.geometry.Point(4.35222222, 52.11428333)
    data_to_site2 = {
        "env": my_env,
        "name": "to_site2",
        "geometry": location_to_site2,
        "capacity": total_amount,
        "level": 0,
        "nr_resources": 4,
    }
    to_site2 = Site(**data_to_site2)

    vessels = {}

    for i in range(nr_barges):
        vessels[f"vessel{i}"] = TransportProcessingResource(
            env=my_env,
            name=f"barge_{i}",
            geometry=location_from_site,
            capacity=10,
            compute_v=lambda x: 10,
        )

    # vessel_last wait till whiletask done
    vessel_last = TransportProcessingResource(
        env=my_env,
        name="vessel_last",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10,
    )
    vessels["vessel_last"] = vessel_last

    activities = {}
    for i in range(nr_barges):
        amount = 5  # handle loading
        duration = 2000  # sailing and unloading

        requested_resources = {}
        activities[f"activity{i}"] = model.WhileActivity(
            env=my_env,
            name=f"while_sequential_activity_subcycle{i}",
            registry=registry,
            sub_processes=[
                model.SequentialActivity(
                    env=my_env,
                    name=f"sequential_activity_subcycle{i}",
                    registry=registry,
                    sub_processes=[
                        model.BasicActivity(
                            env=my_env,
                            name="basic activity:" + vessels[f"vessel{i}"].name,
                            registry=registry,
                            duration=duration,
                            additional_logs=[vessels[f"vessel{i}"]],
                        ),
                        get_sailing_empty(
                            my_env, vessels, i, registry, from_site, duration, max_wave
                        ),
                        model.ShiftAmountActivity(
                            env=my_env,
                            name="loading:" + vessels[f"vessel{i}"].name,
                            registry=registry,
                            processor=vessels[f"vessel{i}"],
                            origin=from_site,
                            destination=vessels[f"vessel{i}"],
                            amount=amount,
                            duration=500 * amount,
                            requested_resources=requested_resources,
                        ),
                        model.MoveActivity(
                            env=my_env,
                            name="sailing full:" + vessels[f"vessel{i}"].name,
                            registry=registry,
                            mover=vessels[f"vessel{i}"],
                            destination=to_site,
                            duration=duration,
                        ),
                        model.ShiftAmountActivity(
                            env=my_env,
                            name="unloading:" + vessels[f"vessel{i}"].name,
                            registry=registry,
                            processor=vessels[f"vessel{i}"],
                            origin=vessels[f"vessel{i}"],
                            destination=to_site,
                            amount=amount,
                            duration=duration,
                            requested_resources=requested_resources,
                        ),
                    ],
                )
            ],
            condition_event=[
                {
                    "type": "container",
                    "concept": to_site,
                    "state": "full",
                    "id_": "default_reservations",
                }
            ],
            start_event={
                "type": "time",
                "start_time": start_delay,
            },
        )

    # now add activity for vessel last, once v1 and v2 are done
    requested_resources = {}
    amount = 5
    duration = 100
    activities["activity_vessel0"] = model.SequentialActivity(
        env=my_env,
        name="sequential_v0",
        registry=registry,
        sub_processes=[
            model.BasicActivity(
                env=my_env,
                name="basic activity vessel_last",
                registry=registry,
                duration=duration,
                additional_logs=[vessel_last],
                start_event=[
                    {
                        "name": "while_sequential_activity_subcycle1",
                        "type": "activity",
                        "state": "done",
                    }
                ],
            ),
            model.MoveActivity(
                env=my_env,
                name="sailing empty: vessel_last",
                registry=registry,
                mover=vessel_last,
                destination=from_site,
                duration=duration,
            ),
            model.ShiftAmountActivity(
                env=my_env,
                name="loading vessel_last",
                registry=registry,
                processor=vessel_last,
                origin=from_site,
                destination=vessel_last,
                amount=amount,
                duration=500 * amount,
                requested_resources=requested_resources,
            ),
            model.MoveActivity(
                env=my_env,
                name="sailing full vessel_last",
                registry=registry,
                mover=vessel_last,
                destination=to_site2,
                duration=duration,
            ),
            model.ShiftAmountActivity(
                env=my_env,
                name="unloading vessel_last",
                registry=registry,
                processor=vessel_last,
                origin=vessel_last,
                destination=to_site2,
                amount=amount,
                duration=duration,
                requested_resources=requested_resources,
            ),
        ],
    )

    model.register_processes(list(activities.values()))
    my_env.run()

    return {
        "env": my_env,
        "object_list": [from_site, to_site, to_site2] + list(vessels.values()),
        "activity_list": list(activities.values()),
    }


def demo_data_simple(env=None):
    """Run a simulation with a single while-sequential loop."""
    if env is None:
        my_env = simpy.Environment(initial_time=0)
    else:
        my_env = env(initial_time=0)

    # create a Site object based on desired mixin classes
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

    # create a TransportProcessingResource object based on desired mixin classes
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

    # prepare input data for from_site
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": 100,
        "level": 100,
    }
    # instantiate from_site
    from_site = Site(**data_from_site)

    # prepare input data for to_site
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {
        "env": my_env,
        "name": "to_site",
        "geometry": location_to_site,
        "capacity": 100,
        "level": 0,
    }
    # instantiate to_site
    to_site = Site(**data_to_site)

    # prepare input data for vessel_01
    data_vessel01 = {
        "env": my_env,
        "name": "vessel01",
        "geometry": location_from_site,
        "loading_rate": 0.0004,
        "unloading_rate": 0.0004,
        "capacity": 4,
        "compute_v": lambda x: 10,
    }
    # instantiate vessel_01
    vessel01 = TransportProcessingResource(**data_vessel01)

    # create a list of the sub processes
    registry = {}
    sub_processes = [
        model.MoveActivity(
            env=my_env,
            name="sailing empty",
            registry=registry,
            mover=vessel01,
            destination=from_site,
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name="loading",
            registry=registry,
            processor=vessel01,
            origin=from_site,
            destination=vessel01,
            amount=4,
            duration=1000,
        ),
        model.MoveActivity(
            env=my_env,
            name="sailing full",
            registry=registry,
            mover=vessel01,
            destination=to_site,
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name="unloading",
            registry=registry,
            processor=vessel01,
            origin=vessel01,
            destination=to_site,
            amount=4,
            duration=1000,
        ),
        model.BasicActivity(
            env=my_env,
            name="basic activity",
            registry=registry,
            duration=0,
            additional_logs=[vessel01],
        ),
    ]

    # create a 'sequential activity' that is made up of the 'sub_processes'
    sequential_activity = model.SequentialActivity(
        env=my_env,
        name="sequential",
        registry=registry,
        sub_processes=sub_processes,
    )

    # create a while activity that executes the 'sequential activity'
    # while the stop condition is not triggered
    while_activity = model.WhileActivity(
        env=my_env,
        name="while",
        registry=registry,
        sub_processes=[sequential_activity],
        condition_event=[{"type": "container", "concept": to_site, "state": "full"}],
    )

    model.register_processes([while_activity])
    my_env.run()

    return {
        "env": my_env,
        "object_list": [from_site, to_site, vessel01],
        "activity_list": [while_activity],
    }
