""" testcase with some delay """ ""
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugins

# setup environment
simulation_start = 0
my_env = simpy.Environment(initial_time=simulation_start)


def getActivitiesAndObjects(scenario=1):
    """
    get result from simulation with two barges with a 100% sailing empty delay %
    Optional if
        scenario 1 a last vessel starts when to_site is full
        scenario 2 a last vessel starts when while activity vessel 1 is done and vessel 1 starts after certain time


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

    total_amount = 30
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": 2 * total_amount,
        "level": 2 * total_amount,
        "nr_resources": 4,
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

    vessel1 = TransportProcessingResource(
        env=my_env,
        name=f"barge1",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10,
    )

    vessel2 = TransportProcessingResource(
        env=my_env,
        name=f"barge2",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10,
    )

    # vessel_last wait till to site is full
    vessel_last = TransportProcessingResource(
        env=my_env,
        name=f"vessel_last",
        geometry=location_from_site,
        capacity=10,
        compute_v=lambda x: 10,
    )

    if scenario != 1:
        # we inlude a wait for activity finished and a wait based on time
        start_event_last_vessel = [
            {
                "name": f"{vessel2.name}: while_activity",
                "type": "activity",
                "state": "done",
            }
        ]
        start_time_vessel1 = 5000
        start_time_vessel2 = 1000
    else:
        start_time_vessel1 = 0
        start_event_last_vessel = None
        start_time_vessel2 = 0

    # create tasks
    registry = {}
    vessel_1_task = delay_while_activity(
        vessel1,
        from_site,
        to_site,
        registry,
        start_time=start_time_vessel1,
        condition_level=10,
    )
    vessel_2_task = delay_while_activity(
        vessel2,
        from_site,
        to_site,
        registry,
        start_time=start_time_vessel2,
        condition_level=100,
    )
    last_task = activity_after(
        vessel_last, to_site, to_site2, registry, start_event=start_event_last_vessel
    )

    main_activities = [vessel_1_task, vessel_2_task, last_task]
    model.register_processes(main_activities)
    my_env.run()

    # construct a list of the main simulation objects
    main_objects = [vessel1, vessel2, vessel_last, from_site, to_site, to_site2]
    return main_activities, main_objects


def delay_while_activity(
    vessel, from_site, to_site, registry, start_time=0, condition_level=100
):
    """main while activity with some planned delays"""
    if condition_level == 100:
        condition_event = {
            "type": "container",
            "concept": to_site,
            "state": "full",
        }
    else:
        # assuming value ok with site
        condition_event = {
            "type": "container",
            "concept": to_site,
            "state": "gt",
            "level": condition_level,
        }
    # delay for boat
    DelayMoveActivity = type(
        "TestMoveActivity",
        (
            plugins.HasDelayPlugin,
            model.MoveActivity,  # the order is critical!
        ),
        {},
    )
    DelaySequenceActivity = type(
        "TestShiftActivity",
        (
            plugins.HasDelayPlugin,
            model.SequentialActivity,  # the order is critical!
        ),
        {},
    )
    DelayWhileActivity = type(
        "TestShiftActivity",
        (
            plugins.HasDelayPlugin,
            model.WhileActivity,  # the order is critical!
        ),
        {},
    )
    amount = 5  # handle loading
    duration = 2000  # sailing and unloading

    # boat 1
    requested_resources = {}
    while_activity_delay = DelayWhileActivity(
        env=my_env,
        name=f"{vessel.name}: while_activity",
        registry=registry,
        sub_processes=[
            DelaySequenceActivity(
                env=my_env,
                name=f"{vessel.name}: sequential_activity",
                registry=registry,
                sub_processes=[
                    model.BasicActivity(
                        env=my_env,
                        name=f"{vessel.name}: basic activity",
                        registry=registry,
                        duration=duration,
                        additional_logs=[vessel],
                    ),
                    DelayMoveActivity(
                        env=my_env,
                        name=f"{vessel.name}: sailing empty delay",
                        registry=registry,
                        mover=vessel,
                        duration=(duration + (500 * amount)) / 2,
                        destination=from_site,
                        delay_percentage=100,
                    ),
                    model.ShiftAmountActivity(
                        env=my_env,
                        name=f"{vessel.name}: loading",
                        registry=registry,
                        processor=vessel,
                        origin=from_site,
                        destination=vessel,
                        amount=amount,
                        duration=500 * amount,
                        requested_resources=requested_resources,
                    ),
                    model.MoveActivity(
                        env=my_env,
                        name=f"{vessel.name}: sailing full",
                        registry=registry,
                        mover=vessel,
                        destination=to_site,
                        duration=duration,
                    ),
                    model.ShiftAmountActivity(
                        env=my_env,
                        name=f"{vessel.name}: unloading",
                        registry=registry,
                        processor=vessel,
                        origin=vessel,
                        destination=to_site,
                        amount=amount,
                        duration=duration,
                        requested_resources=requested_resources,
                    ),
                ],
            )
        ],
        start_event={"type": "time", "start_time": start_time},
        condition_event=[condition_event],
    )
    return while_activity_delay


def activity_after(vessel, to_site, to_site2, registry, start_event=None):
    """additonal loop when other boats are done"""

    if start_event is None:
        start_event = [
            {
                "type": "container",
                "concept": to_site,
                "state": "full",
            }
        ]

    # now add activity for vessel last, once v1 and v2 are done
    requested_resources = {}
    amount = 5
    duration = 100
    activity_last = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name}: seq",
        registry=registry,
        sub_processes=[
            model.BasicActivity(
                env=my_env,
                name=f"{vessel.name}: basic activity",
                registry=registry,
                duration=duration,
                additional_logs=[vessel],
                start_event=start_event,
            ),
            model.MoveActivity(
                env=my_env,
                name=f"{vessel.name}: sailing empty",
                registry=registry,
                mover=vessel,
                destination=to_site,
                duration=duration,
            ),
            model.ShiftAmountActivity(
                env=my_env,
                name=f"{vessel.name}:loading",
                registry=registry,
                processor=vessel,
                origin=to_site,
                destination=vessel,
                amount=amount,
                duration=500 * amount,
                requested_resources=requested_resources,
            ),
            model.MoveActivity(
                env=my_env,
                name=f"{vessel.name}: sailing full",
                registry=registry,
                mover=vessel,
                destination=to_site2,
                duration=duration,
            ),
            model.ShiftAmountActivity(
                env=my_env,
                name=f"{vessel.name}: unloading",
                registry=registry,
                processor=vessel,
                origin=vessel,
                destination=to_site2,
                amount=amount,
                duration=duration,
                requested_resources=requested_resources,
            ),
        ],
    )
    return activity_last
