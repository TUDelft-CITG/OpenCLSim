"""
Tests for openclsim.critical_path.dependencies_from_recorded_activities module
"""

from openclsim.critical_path.dependencies_from_recorded_activities import (
    BaseCP,
    DependenciesFromRecordedActivities,
)


def test_init(simulation_2_barges):
    """Test initialisation."""
    my_cp = DependenciesFromRecordedActivities(**simulation_2_barges)
    assert hasattr(my_cp, "get_dependency_list") and callable(
        getattr(my_cp, "get_dependency_list")
    ), "this method 'get_dependency_list' should exist!"
    assert issubclass(
        DependenciesFromRecordedActivities, BaseCP
    ), "should be child of BaseCP"


def test_get_dependency_list(simulation_2_barges):
    """Test get dependency list."""
    my_cp = DependenciesFromRecordedActivities(**simulation_2_barges)
    dependency_list = my_cp.get_dependency_list()
    assert len(dependency_list) == 113, "113 dependencies expected"
    assert len(set(dependency_list)) == 113, "113 (non duplicate) dependencies expected"
    cp_ids = {item for dependecy_tuple in dependency_list for item in dependecy_tuple}
    assert cp_ids.issubset(
        set(my_cp.recorded_activities_df.cp_activity_id)
    ), "activity IDs must exist in recorded_activities_df"
