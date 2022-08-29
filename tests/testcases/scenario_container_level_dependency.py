"""
Provides a container level dependency scenario.

One vessel is set to transport goods from A to B (short distance, small
vessel), another large vessel will transport from B to C. But only once the
level at B reaches the full capacity of the second vessel.


Call with ``getActivitiesAndObjects()`` as follows:

.. code-block::

    from scenario_container_level_dependency import getActivitiesAndObjects

    act, obj = getActivitiesAndObjects(scenario=1)

"""

import shapely.geometry
# %% Import libraries
import simpy

import openclsim.core as core
import openclsim.model as model

# %% setup environment
simulation_start = 0
my_env = simpy.Environment(initial_time=simulation_start)

# %% Site
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


# %% Transport resource
TransportResource = type(
    "TransportResource",
    (
        core.Identifiable,
        core.Log,
        core.Processor,
        core.ContainerDependentMovable,
        core.HasResource,
    ),
    {},
)


# %% creation of a while activity
def TransportWhileActivityA(vessel, from_site, to_site, registry):
    # the individual steps
    sub_processes_single_run = [
        model.ShiftAmountActivity(
            env=my_env,
            name=f"{vessel.name}: loading",
            registry=registry,
            processor=vessel,
            origin=from_site,
            destination=vessel,
            amount=vessel.container.get_capacity(),
            duration=100 * vessel.container.get_capacity(),
        ),
        model.MoveActivity(
            env=my_env,
            name=f"{vessel.name}: sailing full",
            registry=registry,
            mover=vessel,
            destination=to_site,
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name=f"{vessel.name}: unloading",
            registry=registry,
            processor=vessel,
            origin=vessel,
            destination=to_site,
            amount=vessel.container.get_capacity(),
            duration=150 * vessel.container.get_capacity(),
        ),
        model.MoveActivity(
            env=my_env,
            name=f"{vessel.name}: sailing empty",
            registry=registry,
            mover=vessel,
            destination=from_site,
        ),
    ]

    # the sequential activity
    sequential_activity = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name}: sequential_activity_transport",
        registry=registry,
        sub_processes=sub_processes_single_run,
    )

    # the while activity
    while_activity = model.WhileActivity(
        env=my_env,
        name=f"{vessel.name}: transport process",
        registry=registry,
        sub_processes=[sequential_activity],
        condition_event=[{"type": "container", "concept": from_site, "state": "empty"}],
    )

    # the initial move activity towards the from_site just in case
    initial_move = model.MoveActivity(
        env=my_env,
        name=f"{vessel.name}: sailing towards from_site",
        registry=registry,
        mover=vessel,
        destination=from_site,
    )

    # the main sequential activity (move to from_site, and then while loop)
    main_activity = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name}: main transporting activity",
        registry=registry,
        sub_processes=[initial_move, while_activity],
    )

    return main_activity


def TransportWhileActivityB(vessel, from_site, to_site, registry):
    # the individual steps
    sub_processes_single_run = [
        model.ShiftAmountActivity(
            env=my_env,
            name=f"{vessel.name}: loading",
            registry=registry,
            processor=vessel,
            origin=from_site,
            destination=vessel,
            amount=vessel.container.get_capacity(),
            start_event=[
                {
                    "type": "container",
                    "concept": from_site,
                    "state": "ge",
                    "level": vessel.container.get_capacity(),
                }
            ],
            duration=100 * vessel.container.get_capacity(),
        ),
        model.MoveActivity(
            env=my_env,
            name=f"{vessel.name}: sailing full",
            registry=registry,
            mover=vessel,
            destination=to_site,
        ),
        model.ShiftAmountActivity(
            env=my_env,
            name=f"{vessel.name}: unloading",
            registry=registry,
            processor=vessel,
            origin=vessel,
            destination=to_site,
            amount=vessel.container.get_capacity(),
            duration=150 * vessel.container.get_capacity(),
        ),
        model.MoveActivity(
            env=my_env,
            name=f"{vessel.name}: sailing empty",
            registry=registry,
            mover=vessel,
            destination=from_site,
        ),
    ]

    # the sequential activity
    sequential_activity = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name}: sequential_activity_transport",
        registry=registry,
        sub_processes=sub_processes_single_run,
    )

    # the while activity
    while_activity = model.WhileActivity(
        env=my_env,
        name=f"{vessel.name}: transport process",
        registry=registry,
        sub_processes=[sequential_activity],
        condition_event=[{"type": "container", "concept": to_site, "state": "full"}],
    )

    # the initial move activity towards the from_site just in case
    initial_move = model.MoveActivity(
        env=my_env,
        name=f"{vessel.name}: sailing towards from_site",
        registry=registry,
        mover=vessel,
        destination=from_site,
    )

    # the main sequential activity (move to from_site, and then while loop)
    main_activity = model.SequentialActivity(
        env=my_env,
        name=f"{vessel.name}: main transporting activity",
        registry=registry,
        sub_processes=[initial_move, while_activity],
    )

    return main_activity


# %%
def getActivitiesAndObjects(scenario=1):
    """
    Main function for running a simulation.

    This function runs a simulation with two vessels transporting goods from
    site A to site C, with a transfer at site B. The second vessel is larger
    and will wait for the level at site B to at least reach the vessel capacity
    before loading and sailing off.

    Two scenario's can be chosen: (1) the small vessel can keep up with the
    large one (the large one will not have to wait), and (2) the opposite where
    the large vessel has to wait between trips.

    Returns (1) a list of the main simulation activities, and (2) the main
    simulation objects (vessels and sites).
    """
    if scenario == 1:
        cap_large_vessel = 3
    elif scenario == 2:
        cap_large_vessel = 5
    else:
        raise ValueError("Choose from scenario 1 or 2")

    registry = {}

    # prepare sites
    location_A = shapely.geometry.Point(4.18, 52.18)
    data_site_A = {
        "env": my_env,
        "name": "from_site A",
        "geometry": location_A,
        "capacity": 20,
        "level": 20,
        "nr_resources": 1,
    }
    site_A = Site(**data_site_A)

    location_B = shapely.geometry.Point(4.22, 52.15)
    data_site_B = {
        "env": my_env,
        "name": "transfer_site B",
        "geometry": location_B,
        "capacity": 20,
        "level": 0,
        "nr_resources": 2,
    }
    site_B = Site(**data_site_B)

    # prepare sites
    location_C = shapely.geometry.Point(4.50, 52.00)
    data_site_C = {
        "env": my_env,
        "name": "to_site C",
        "geometry": location_C,
        "capacity": 20,
        "level": 0,
        "nr_resources": 1,
    }
    site_C = Site(**data_site_C)

    # create vessel objects
    vessel_a = TransportResource(
        env=my_env,
        name="small vessel",
        geometry=location_A,
        capacity=1,
        compute_v=lambda x: 10,
    )

    vessel_b = TransportResource(
        env=my_env,
        name="large vessel",
        geometry=location_A,
        capacity=cap_large_vessel,
        compute_v=lambda x: 15,
    )

    # create tasks
    vessel_a_task = TransportWhileActivityA(vessel_a, site_A, site_B, registry)
    vessel_b_task = TransportWhileActivityB(vessel_b, site_B, site_C, registry)

    # make it a parallel
    parallel = model.ParallelActivity(
        env=my_env,
        name="full transporting process",
        registry=registry,
        sub_processes=[vessel_a_task, vessel_b_task],
    )

    # run the simulation
    main_activities = [parallel]
    model.register_processes(main_activities)
    my_env.run()

    # construct a list of the main simulation objects
    main_objects = [vessel_a, vessel_b, site_A, site_B, site_C]

    return main_activities, main_objects
