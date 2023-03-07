"""
Tests for openclsim.critical_path.dependencies_from_simpy module
"""
import shapely.geometry
import simpy.events

import openclsim.core as core
import openclsim.model as model


from openclsim.critical_path.dependencies_from_simpy_step import (
    MyCustomSimpyEnv,
    DependenciesFromSimpy,
)


def demo_data(nr_barges, total_amount):
    """
    Run a simulation where <nr_barges> barges need to shift an amount of <total_amount>
    from site 1 to site 2 whereafter a larger vessel can come into action.

    Parameters
    ----------
    nr_barges : int
        Number of barges in the simulation.
    total_amount : int
        Total amount to be transported in the simulation.
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
    my_env = MyCustomSimpyEnv(initial_time=simulation_start)
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


def test_init(simulation_2_barges):
    """Test initialisation."""
    import pandas as pd
    simulation_2_barges = demo_data(2, 100)
    my_env = simulation_2_barges['env']
    df_step = pd.DataFrame(my_env.data_step,
                           columns=['t', 'e_id', 'type', 'value', 'prio', 'event_object']).set_index('e_id')
    df_cause_effect = pd.DataFrame(my_env.data_cause_effect,
                                   columns=['e_id_cause', 'e_id_effect']).set_index('e_id_cause')
    list_cause_effect = my_env.data_cause_effect

    # we want dependencies based on the timeouts as seen in recorded activities!
    # so loop through df_cause_effect until no longer possible and make only timeout dependency tuples!
    def _loop_through(e_id_cause, prev_timeout=None, dependency_list=None, seen_eids=None, all_tuples=None):

        # init when called for very first time
        if dependency_list is None:
            dependency_list = []
        if seen_eids is None:
            seen_eids = {e_id_cause}
        else:
            seen_eids.add(e_id_cause)
        if all_tuples is None:
            all_tuples = []

        # see if timeout
        if isinstance(df_step.loc[e_id_cause, 'event_object'], simpy.events.Timeout):
            # yep dealing with a timeOut!
            if df_step.loc[e_id_cause, 'value'] is None:
                our_reference = "unknown_openclsim_reference"
            else:
                our_reference = df_step.loc[e_id_cause, 'value']
            print(f"TimeOut with delay {df_step.loc[e_id_cause, 'event_object']._delay} {our_reference}")
            if prev_timeout is not None:
                print("Adding OpenCLSim dependency :)")
                dependency_list.append((prev_timeout, our_reference))
            prev_timeout = our_reference

        # see if effect and call recursive self again
        new_tuples = [tup for tup in list_cause_effect if tup[0] == e_id_cause]
        all_tuples = new_tuples + all_tuples

        if len(all_tuples) > 0:
            print(f"Passing eid {all_tuples[0][1]}")
            return _loop_through(all_tuples[0][1],
                                 prev_timeout=prev_timeout,
                                 dependency_list=dependency_list,
                                 seen_eids=seen_eids, all_tuples=all_tuples[1:])
        else:
            # this id does not causes stuff done
            print(f"{e_id_cause} causes NO effect")
            return dependency_list, seen_eids

    all_dependencies = []
    remaining_eids = {tup[0] for tup in list_cause_effect}
    while len(remaining_eids) > 0:
        found_dependencies, seen_eids = _loop_through(list(remaining_eids)[0])
        all_dependencies = all_dependencies + found_dependencies
        remaining_eids = remaining_eids - seen_eids





def test_get_dependency_list(simulation_2_barges):
    """test get dependency list"""
    my_cp = DependenciesFromRecordedActivities(**simulation_2_barges)
    dependency_list = my_cp.get_dependency_list()
    assert len(dependency_list) == 113, "113 dependencies expected"
    assert len(set(dependency_list)) == 113, "113 (non duplicate) dependencies expected"
    cp_ids = {item for dependecy_tuple in dependency_list for item in dependecy_tuple}
    assert cp_ids.issubset(
        set(my_cp.recorded_activities_df.cp_activity_id)
    ), "activity IDs must exist in recored_activities_df"
