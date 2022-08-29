import datetime
import datetime as dt

import numpy as np
import pandas as pd
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugin

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
        core.HasResource,  # NB: LoadingFunction and UnloadingFunction are not mixed in
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
# initialise registry
registry = {}


def make_meteo_df():
    """make meteo dataframe"""
    daterange = pd.date_range(
        dt.datetime(2010, 1, 1), dt.datetime(2020, 12, 31), freq=dt.timedelta(hours=1)
    )
    count_time = [
        (t - dt.datetime(2010, 1, 1)).total_seconds() / 3600 for t in daterange
    ]
    wave_height = np.abs(
        [
            0.5 * np.sin(t / 5) + np.sin(t / 20) + np.sin(t / 50) + np.sin(t / 100)
            for t in count_time
        ]
    )
    df_meteo = pd.DataFrame(wave_height, index=daterange, columns=["Hs"])
    df_meteo.loc[:, "ts"] = df_meteo.index.values.astype(float) / 1_000_000_000
    return df_meteo


def get_while_activity(
    my_env, vessel, from_site, to_site, sailing_crit_max=2.0, loading_crit_max=1.5
):
    """whila activity for vessel"""
    df_meteo = make_meteo_df()

    # stuphid bugfix

    if vessel.name == "vessel01":
        cd_event = {"type": "container", "concept": to_site, "state": "full"}
    else:
        cd_event = {
            "type": "container",
            "concept": to_site,
            "state": "ge",
            "level": to_site.container.get_capacity() / 2,
        }

    # generate a weather criterion for the sailing process
    sailing_crit = plugin.WeatherCriterion(
        name="sailing_crit",
        condition="Hs",
        maximum=sailing_crit_max,
        window_length=3600,
    )

    # generate a weather criterion for the loading process
    loading_crit = plugin.WeatherCriterion(
        name="loading_crit",
        condition="Hs",
        maximum=loading_crit_max,
        window_length=3600,
    )

    # create a list of the sub processes
    sub_processes = [
        TestMoveActivity(
            env=my_env,
            name=f"{vessel.name} sailing empty",
            registry=registry,
            mover=vessel,
            destination=from_site,
            metocean_criteria=sailing_crit,
            metocean_df=df_meteo,
        ),
        TestShiftActivity(
            env=my_env,
            name=f"{vessel.name} loading",
            registry=registry,
            processor=vessel,
            origin=from_site,
            destination=vessel,
            amount=4,
            duration=3600,
            metocean_criteria=loading_crit,
            metocean_df=df_meteo,
        ),
        TestMoveActivity(
            env=my_env,
            name=f"{vessel.name} sailing full",
            registry=registry,
            mover=vessel,
            destination=to_site,
            metocean_criteria=sailing_crit,
            metocean_df=df_meteo,
        ),
        TestShiftActivity(
            env=my_env,
            name=f"{vessel.name} unloading",
            registry=registry,
            processor=vessel,
            origin=vessel,
            destination=to_site,
            amount=4,
            duration=3600,
            metocean_criteria=loading_crit,
            metocean_df=df_meteo,
        ),
    ]

    # create a 'sequential activity' that is made up of the 'sub_processes'
    sequential_activity = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name} sequential_activity_subcycle",
        registry=registry,
        sub_processes=sub_processes,
    )

    # create a while activity that executes the 'sequential activity' while the stop condition is not triggered
    while_activity = model.WhileActivity(
        env=my_env,
        name=f"{vessel.name} while_sequential_activity_subcycle",
        registry=registry,
        sub_processes=[sequential_activity],
        condition_event=[cd_event],
    )

    return while_activity


def getActivitiesAndObjects(year=None):
    """run simulation with weather"""
    if year is None:
        year = 2017
    df_meteo = make_meteo_df()
    simulation_start = datetime.datetime(year, 1, 1, 0, 0)
    my_env = simpy.Environment(initial_time=simulation_start.timestamp())

    # prepare input data for from_site
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": 1500,
        "level": 1500,
    }
    # instantiate from_site
    from_site = Site(**data_from_site)

    # prepare input data for to_site
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {
        "env": my_env,
        "name": "to_site",
        "geometry": location_to_site,
        "capacity": 800,
        "level": 0,
    }
    # instantiate to_site
    to_site = Site(**data_to_site)

    # prepare input data for vessel_01
    data_vessel01 = {
        "env": my_env,
        "name": "vessel01",
        "geometry": location_from_site,
        "capacity": 4,
        "compute_v": lambda x: 10,
    }
    # prepare input data for vessel_01
    data_vessel02 = {
        "env": my_env,
        "name": "vessel02",
        "geometry": location_from_site,
        "capacity": 4,
        "compute_v": lambda x: 50,
    }
    # instantiate vessel_01
    vessel01 = TransportProcessingResource(**data_vessel01)
    vessel02 = TransportProcessingResource(**data_vessel02)

    # get while activities
    while1 = get_while_activity(
        my_env, vessel01, from_site, to_site, sailing_crit_max=2, loading_crit_max=1.5
    )
    while2 = get_while_activity(
        my_env, vessel02, from_site, to_site, sailing_crit_max=1.4, loading_crit_max=1.4
    )

    model.register_processes([while1, while2])
    my_env.run()

    return [while1, while2], [from_site, to_site, vessel01, vessel02]

    #     "env": my_env,
    #     "registry": registry,
    #     "from_site": from_site,
    #     "to_site": to_site,
    #     "vessel01": vessel01,
    #     "loading_crit": loading_crit,
    #     "sailing_crit": sailing_crit,
    #     "activitities": [while_activity]
    # }
