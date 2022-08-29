"""
Provides a resource dependency scenario with two vessels sharing an unloading
site with a single resource.

Call with ``getActivitiesAndObjects()`` as follows:

.. code-block::

    from scenario_resource_dependency import getActivitiesAndObjects

    act, obj = getActivitiesAndObjects()

"""

import shapely.geometry
# %% Import libraries
import simpy

import openclsim.core as core
import openclsim.model as model

# %% setup environment
simulation_start = 0
my_env = simpy.Environment(initial_time=simulation_start)
registry = {}

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
def SingleRun(vessel, from_site, to_site):
    """single run for vessel"""
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

    return sequential_activity


def WhileParallel(vessel1, vessel2, from_site, to_site):
    """define while activitity with parallel in it"""
    parallel = model.ParallelActivity(
        env=my_env,
        name="parallel",
        registry=registry,
        sub_processes=[
            SingleRun(vessel1, from_site, to_site),
            SingleRun(vessel2, from_site, to_site),
        ],
    )
    # the while activity
    while_activity = model.WhileActivity(
        env=my_env,
        name=f"the big while",
        registry=registry,
        sub_processes=[parallel],
        condition_event=[{"type": "container", "concept": from_site, "state": "empty"}],
    )
    return while_activity


# %%
def getActivitiesAndObjects():
    """
    Main function for running a simulation.

    This function runs a simulation with two vessels transporting goods from
    site s1 to site s2, where s1 has a resource limitation: it can load one
    ship at a time.

    Vessels will have different sailing speeds.

    Returns (1) a list of the main simulation activities, and (2) the main
    simulation objects (vessels and sites)
    """

    # prepare input data for from_site
    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)
    data_from_site = {
        "env": my_env,
        "name": "from_site",
        "geometry": location_from_site,
        "capacity": 51,
        "level": 51,
        "nr_resources": 10,
    }
    from_site = Site(**data_from_site)

    # prepare input data for to_site
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)
    data_to_site = {
        "env": my_env,
        "name": "to_site",
        "geometry": location_to_site,
        "capacity": 50,
        "level": 0,
        "nr_resources": 1,
    }
    to_site = Site(**data_to_site)

    # create vessel objects
    vessel_a = TransportResource(
        env=my_env,
        name="vessel_a",
        geometry=location_from_site,
        capacity=2,
        compute_v=lambda x: 10,
    )

    vessel_b = TransportResource(
        env=my_env,
        name="vessel_b",
        geometry=location_from_site,
        capacity=1,
        compute_v=lambda x: 10,
    )

    # run the simulation
    main_activities = [WhileParallel(vessel_a, vessel_b, from_site, to_site)]
    model.register_processes(main_activities)
    my_env.run()

    # construct a list of the main simulation objects
    main_objects = [vessel_a, vessel_b, from_site, to_site]

    return main_activities, main_objects
