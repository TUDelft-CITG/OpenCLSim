"""
Fixtures for the test-suite.
"""
import pytest
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
from openclsim.critical_path.dependencies_from_simpy_step import MyCustomSimpyEnv


@pytest.fixture()
def simulation_2_barges():
    """
    Fixture returns the simpy.Environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(nr_barges=2, total_amount=100)


@pytest.fixture()
def simulation_2_barges_custom_env():
    """
    Fixture returns the custom environment, objects and activities after a 2-barges simulation.
    """
    return demo_data(nr_barges=2, total_amount=100, env=MyCustomSimpyEnv)


@pytest.fixture()
def dependencies_simulation_2_barges():
    """
    List of dependencies for simulation '2 barges' with index values (since UUID changes)
    """
    dependency_list = [
        (1, 3),
        (2, 4),
        (3, 5),
        (5, 7),
        (5, 9),
        (9, 10),
        (7, 12),
        (10, 13),
        (12, 14),
        (13, 16),
        (14, 17),
        (16, 18),
        (17, 20),
        (18, 21),
        (20, 21),
        (18, 23),
        (23, 24),
        (21, 26),
        (24, 27),
        (26, 28),
        (27, 30),
        (28, 31),
        (30, 32),
        (31, 34),
        (32, 35),
        (34, 35),
        (32, 37),
        (37, 38),
        (35, 40),
        (38, 41),
        (40, 42),
        (41, 44),
        (42, 45),
        (44, 46),
        (45, 48),
        (46, 49),
        (48, 49),
        (46, 51),
        (51, 52),
        (49, 54),
        (52, 55),
        (54, 56),
        (55, 58),
        (56, 59),
        (58, 60),
        (59, 62),
        (60, 63),
        (62, 63),
        (60, 65),
        (65, 66),
        (63, 68),
        (66, 69),
        (68, 70),
        (69, 72),
        (70, 73),
        (72, 74),
        (73, 76),
        (74, 77),
        (76, 77),
        (74, 79),
        (79, 80),
        (77, 82),
        (80, 83),
        (82, 84),
        (83, 86),
        (84, 87),
        (86, 88),
        (87, 90),
        (88, 91),
        (90, 91),
        (88, 93),
        (93, 94),
        (91, 96),
        (94, 97),
        (96, 98),
        (97, 100),
        (98, 101),
        (100, 102),
        (101, 104),
        (102, 105),
        (104, 105),
        (102, 107),
        (107, 108),
        (105, 110),
        (108, 111),
        (110, 112),
        (111, 114),
        (112, 115),
        (114, 116),
        (115, 118),
        (116, 119),
        (118, 119),
        (116, 121),
        (121, 122),
        (119, 124),
        (122, 125),
        (124, 126),
        (125, 128),
        (126, 129),
        (128, 130),
        (129, 132),
        (130, 133),
        (132, 133),
        (130, 135),
        (135, 136),
        (133, 138),
        (138, 139),
        (0, 141),
        (139, 141),
        (141, 142),
        (142, 143),
        (143, 145),
        (145, 146),
    ]
    return dependency_list


@pytest.fixture()
def simulation_4_barges():
    """
    Fixture returns the simpy.Environment, objects and activities after a 4-barges simulation.
    """
    return demo_data(nr_barges=4, total_amount=100)


def demo_data(nr_barges, total_amount, env=None):
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
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.HasResource,
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
                        model.MoveActivity(
                            env=my_env,
                            name="sailing empty:" + vessels[f"vessel{i}"].name,
                            registry=registry,
                            mover=vessels[f"vessel{i}"],
                            destination=from_site,
                            duration=duration,
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
    """ Run a simulation with a single while-sequential loop. """
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

    # prepare input data for from_site
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    data_from_site = {"env": my_env,
                      "name": "from_site",
                      "geometry": location_from_site,
                      "capacity": 100,
                      "level": 100
                      }
    # instantiate from_site
    from_site = Site(**data_from_site)

    # prepare input data for to_site
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {"env": my_env,
                    "name": "to_site",
                    "geometry": location_to_site,
                    "capacity": 100,
                    "level": 0
                    }
    # instantiate to_site
    to_site = Site(**data_to_site)

    # prepare input data for vessel_01
    data_vessel01 = {"env": my_env,
                     "name": "vessel01",
                     "geometry": location_from_site,
                     "loading_rate": 0.0004,
                     "unloading_rate": 0.0004,
                     "capacity": 4,
                     "compute_v": lambda x: 10
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

