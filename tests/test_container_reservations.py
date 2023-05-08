"""Test application for the container reservations."""

import pandas as pd
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_container_reservations():
    """Test application for the container reservations."""
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
            core.Processor,
            core.HasResource,
            core.ContainerDependentMovable,
            core.Identifiable,
            core.Log,
        ),
        {},
    )
    NR_BARGES = 8
    total_amount = 200
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)

    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": total_amount,
        "level": total_amount,
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

    vessels = {}

    for i in range(NR_BARGES):
        vessels[f"vessel{i}"] = TransportProcessingResource(
            env=my_env,
            name=f"barge{i}",
            geometry=location_from_site,
            capacity=10,
            compute_v=lambda x: 10,
        )
    cutter = TransportProcessingResource(
        env=my_env,
        name="cutter",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10,
    )
    vessels["cutter"] = cutter

    activities = {}
    for i in range(NR_BARGES):
        amount = {0: 7, 7: 8, 1: 9, 2: 6, 3: 3, 6: 3, 5: 3, 4: 3}[i]
        duration = {0: 25, 7: 36, 1: 52, 2: 49, 3: 21, 6: 22, 5: 43, 4: 47}[i]

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
                            name=f"basic activity{i}",
                            registry=registry,
                            duration=duration,
                            additional_logs=[vessels[f"vessel{i}"]],
                        ),
                        model.MoveActivity(
                            env=my_env,
                            name=f"sailing empty{i}",
                            registry=registry,
                            mover=vessels[f"vessel{i}"],
                            destination=from_site,
                            duration=duration,
                        ),
                        model.ShiftAmountActivity(
                            env=my_env,
                            name=f"loading{i}",
                            registry=registry,
                            processor=cutter,
                            origin=from_site,
                            destination=vessels[f"vessel{i}"],
                            amount=amount,
                            duration=5 * amount,
                            requested_resources=requested_resources,
                        ),
                        model.MoveActivity(
                            env=my_env,
                            name=f"sailing full{i}",
                            registry=registry,
                            mover=vessels[f"vessel{i}"],
                            destination=to_site,
                            duration=duration,
                        ),
                        model.ShiftAmountActivity(
                            env=my_env,
                            name=f"unloading{i}",
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

    model.register_processes(list(activities.values()))
    my_env.run()

    assert my_env.now == 1175

    for activity in activities.values():
        assert_log(activity)

    for vessel in vessels.values():
        assert_log(vessel)

    assert from_site.container.items == [
        {"id": "default", "capacity": 200, "level": 0},
        {"id": "default_reservations", "capacity": 200, "level": 0},
    ]

    assert to_site.container.items == [
        {"id": "default", "capacity": 200, "level": 200.0},
        {"id": "default_reservations", "capacity": 200, "level": 200.0},
    ]

    data = []
    for i in range(len(vessels.values()) - 1):
        vessel = vessels[f"vessel{i}"]
        activity = activities[f"activity{i}"]
        sub_act = activity.sub_processes[0].sub_processes[-1]
        log = pd.DataFrame(vessel.log)
        nr_trips = len(
            log[(log.ActivityID == sub_act.id) & (log.ActivityState == "START")]
        )
        data.append(
            {
                "name": vessel.name,
                "trips": nr_trips,
            }
        )

    assert data == [
        {"name": "barge0", "trips": 6},
        {"name": "barge1", "trips": 4},
        {"name": "barge2", "trips": 4},
        {"name": "barge3", "trips": 7},
        {"name": "barge4", "trips": 4},
        {"name": "barge5", "trips": 4},
        {"name": "barge6", "trips": 6},
        {"name": "barge7", "trips": 5},
    ]
