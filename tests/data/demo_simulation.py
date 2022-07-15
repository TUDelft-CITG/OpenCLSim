import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

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


def run_simulation(nt_barges, total_amount):
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {"env": my_env,
                      "name": "from_site",
                      "geometry": location_from_site,
                      "capacity": 2 * total_amount,
                      "level": 2 * total_amount,
                      "nr_resources": 1
                      }
    from_site = Site(**data_from_site)

    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {"env": my_env,
                    "name": "to_site",
                    "geometry": location_to_site,
                    "capacity": total_amount,
                    "level": 0,
                    "nr_resources": 4
                    }
    to_site = Site(**data_to_site)

    location_to_site2 = shapely.geometry.Point(4.35222222, 52.11428333)
    data_to_site2 = {"env": my_env,
                     "name": "to_site2",
                     "geometry": location_to_site2,
                     "capacity": total_amount,
                     "level": 0,
                     "nr_resources": 4
                     }
    to_site2 = Site(**data_to_site2)

    vessels = {}

    for i in range(nt_barges):
        vessels[f"vessel{i}"] = TransportProcessingResource(
            env=my_env,
            name=f"barge_{i}",
            geometry=location_from_site,
            capacity=10,
            compute_v=lambda x: 10
        )

    # vessel_last wait till whiletask done
    vessel_last = TransportProcessingResource(
        env=my_env,
        name="vessel_last",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10
    )
    vessels["vessel_last"] = vessel_last

    activities = {}
    for i in range(nt_barges):
        amount = 5  # handle loading
        duration = 2000  # sailing and unloading

        requested_resources = {}
        activities[f"activity{i}"] = model.WhileActivity(
            env=my_env,
            name=f"while_sequential_activity_subcycle{i}",
            registry=registry,
            sub_processes=[model.SequentialActivity(
                env=my_env,
                name=f"sequential_activity_subcycle{i}",
                registry=registry,
                sub_processes=[
                    model.BasicActivity(
                        env=my_env,
                        name="basic activity:" + vessels[f"vessel{i}"].name,
                        registry=registry,
                        duration=duration,
                        additional_logs=[vessels[f"vessel{i}"]],  # TODO add stop event for vessel 1 if...
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
            )],
            condition_event=[
                {
                    "type": "container",
                    "concept": to_site,
                    "state": "full",
                    "id_": "default_reservations"
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
                start_event=[{
                    "name": "while_sequential_activity_subcycle1",
                    "type": "activity",
                    "state": "done"}]
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
        ])

    model.register_processes(list(activities.values()))
    my_env.run()

    return {
        "vessels": vessels,
        "activities": activities,
        "from_site": from_site,
        "to_site": to_site,
        "to_site2": to_site2}
