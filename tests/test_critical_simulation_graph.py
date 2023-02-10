"""
Tests for openclsim.critical_path.simulation_graph module

In order to test the simulation graph creation and the 'get critical path'
we have a hardcoded dependency_list based on index of testdata (which we convert to UUIDs)
"""
import pytest

from openclsim.critical_path.base_cp import BaseCP
from openclsim.critical_path.simulation_graph import SimulationGraph


@pytest.fixture()
def recorded_activities_2_barges(simulation_2_barges):
    TestCP = type(
        "TestCP",
        (BaseCP,),
        {"get_dependency_list": "no need to implement"},
    )
    my_basecp = TestCP(**simulation_2_barges)
    recorded_activities_2_barges = my_basecp.get_recorded_activity_df()
    return recorded_activities_2_barges


def test_get_simulation_graph(
    recorded_activities_2_barges, dependencies_simulation_2_barges
):
    """
    Test creation of simulation_graph in simulation with 2 barges.
    """
    dependency_list = [
        (
            recorded_activities_2_barges.loc[tup[0], "cp_activity_id"],
            recorded_activities_2_barges.loc[tup[1], "cp_activity_id"],
        )
        for tup in dependencies_simulation_2_barges
    ]
    my_graph = SimulationGraph(recorded_activities_2_barges, dependency_list)

    assert len(my_graph.simulation_graph.edges) == len(dependency_list) + len(
        set(recorded_activities_2_barges.cp_activity_id)
    )
    assert len(my_graph.simulation_graph.nodes) == 2 * len(
        set(recorded_activities_2_barges.cp_activity_id)
    )
    assert my_graph.max_duration == 110400
    assert my_graph.n_activities == len(
        set(recorded_activities_2_barges.cp_activity_id)
    )


def test_get_critical_activities(
    recorded_activities_2_barges, dependencies_simulation_2_barges
):
    """get critical activities"""
    dependency_list = [
        (
            recorded_activities_2_barges.loc[tup[0], "cp_activity_id"],
            recorded_activities_2_barges.loc[tup[1], "cp_activity_id"],
        )
        for tup in dependencies_simulation_2_barges
    ]

    my_graph = SimulationGraph(recorded_activities_2_barges, dependency_list)
    critical_activity_list = my_graph.get_list_critical_activities()
    criticial_activities_df = recorded_activities_2_barges.loc[
        recorded_activities_2_barges.cp_activity_id.isin(critical_activity_list), :
    ]
    assert len(critical_activity_list) == 102
    assert criticial_activities_df.Activity.value_counts().to_dict() == {
        "loading:barge_0": 20,
        "loading:barge_1": 20,
        "unloading:barge_1": 20,
        "unloading:barge_0": 18,
        "basic activity:barge_0": 10,
        "sailing empty:barge_0": 10,
        "sailing full:barge_1": 10,
        "sailing full:barge_0": 9,
        "basic activity:barge_1": 9,
        "sailing empty:barge_1": 9,
        "basic activity vessel_last": 2,
        "loading vessel_last": 2,
        "unloading vessel_last": 2,
        "sailing empty: vessel_last": 1,
        "sailing full vessel_last": 1,
    }


def test_get_critical_activities_faulty_dependencies(
    recorded_activities_2_barges, dependencies_simulation_2_barges
):
    """trigger ValueError"""
    dependency_list = [
        (
            recorded_activities_2_barges.loc[tup[0], "cp_activity_id"],
            recorded_activities_2_barges.loc[tup[1], "cp_activity_id"],
        )
        for tup in dependencies_simulation_2_barges
    ]
    # make faulty (reversed dependency for 1 link)
    dependency_list[5] = (dependency_list[5][1], dependency_list[5][0])

    with pytest.raises(ValueError):
        _ = SimulationGraph(recorded_activities_2_barges, dependency_list)
