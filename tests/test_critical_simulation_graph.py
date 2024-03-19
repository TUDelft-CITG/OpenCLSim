"""
Tests for openclsim.critical_path.simulation_graph module

In order to test the simulation graph creation and the 'get critical path'
we have a hardcoded dependency_list based on index of testdata (which we convert to UUIDs)
"""

import pytest

from openclsim.critical_path.dependencies_from_recorded_activities import (
    DependenciesFromRecordedActivities,
)
from openclsim.critical_path.simulation_graph import SimulationGraph


@pytest.fixture()
def simulation_data_2_barges(simulation_2_barges):
    """Fixture that gets some recorded activities and dependencies."""
    my_cp = DependenciesFromRecordedActivities(**simulation_2_barges)
    _ = my_cp.get_recorded_activity_df()
    _ = my_cp.get_dependency_list()
    return my_cp


def test_get_simulation_graph(simulation_data_2_barges):
    """
    Test creation of simulation_graph in simulation with 2 barges.
    """
    my_graph = SimulationGraph(
        simulation_data_2_barges.recorded_activities_df,
        simulation_data_2_barges.dependency_list,
    )

    assert len(my_graph.simulation_graph.edges) == len(
        simulation_data_2_barges.dependency_list
    ) + len(set(simulation_data_2_barges.recorded_activities_df.cp_activity_id))
    assert len(my_graph.simulation_graph.nodes) == 2 * len(
        set(simulation_data_2_barges.recorded_activities_df.cp_activity_id)
    )
    assert my_graph.max_duration == 110400
    assert my_graph.n_activities == len(
        set(simulation_data_2_barges.recorded_activities_df.cp_activity_id)
    )


def test_get_critical_activities(simulation_data_2_barges):
    """get critical activities"""
    my_graph = SimulationGraph(
        simulation_data_2_barges.recorded_activities_df,
        simulation_data_2_barges.dependency_list,
    )
    critical_activity_list = my_graph.get_list_critical_activities()
    criticial_activities_df = simulation_data_2_barges.recorded_activities_df.loc[
        simulation_data_2_barges.recorded_activities_df.cp_activity_id.isin(
            critical_activity_list
        ),
        :,
    ]
    assert len(critical_activity_list) == 102
    assert criticial_activities_df.Activity.value_counts().to_dict() == {
        "loading:barge_0": 30,
        "loading:barge_1": 30,
        "unloading:barge_1": 30,
        "unloading:barge_0": 27,
        "basic activity:barge_0": 20,
        "sailing empty:barge_0": 20,
        "sailing full:barge_1": 20,
        "sailing full:barge_0": 18,
        "basic activity:barge_1": 18,
        "sailing empty:barge_1": 18,
        "basic activity vessel_last": 4,
        "loading vessel_last": 3,
        "unloading vessel_last": 3,
        "sailing empty: vessel_last": 2,
        "sailing full vessel_last": 2,
    }


def test_get_critical_activities_faulty_dependencies(simulation_data_2_barges):
    """trigger ValueError"""
    # make faulty (reversed dependency for 1 link)
    dependency_list = simulation_data_2_barges.dependency_list
    dependency_list[5] = (dependency_list[5][1], dependency_list[5][0])

    with pytest.raises(ValueError):
        _ = SimulationGraph(
            simulation_data_2_barges.recorded_activities_df, dependency_list
        )
