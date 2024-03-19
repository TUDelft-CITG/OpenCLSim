"""
Tests for openclsim.critical_path.dependencies_from_simpy module.
"""

import datetime as dt

from openclsim.critical_path.dependencies_from_simpy_step import (
    CriticalPathEnvironment,
    DependenciesFromSimpy,
)


def test_altered_step_environment():
    """Test AlteredStepEnv."""
    my_env = CriticalPathEnvironment(initial_time=0)
    # do a simple timeout and another and assert what is logged

    def simple_timeout(duration, value):
        _ = yield my_env.timeout(duration, value=value)

    my_env.process(simple_timeout(10, "p10"))
    my_env.process(simple_timeout(15, "p15"))
    my_env.run(until=30)
    assert len(my_env.data_step) == 6, "2 times 3 events expected to have been handled"
    assert (
        len(my_env.data_cause_effect) == 4
    ), "2 times 3 events expected to have been handled"


def test_get_dependency_list(simulation_2_barges_custom_env):
    """Test get_dependency_list method in 2 barge simulation."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    dependency_list = my_cp.get_dependency_list()

    assert len(dependency_list) == 103, "103 dependencies expected"

    # check that all dependencies have zero time diff
    for dep in my_cp.dependency_list:
        t0 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[0]), "end_time"
        ].iloc[0]
        t1 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[1]), "start_time"
        ].iloc[0]
        assert t1 - t0 == dt.timedelta(seconds=0), "dependencies have no len in time!"


def test_get_critical_path_df(simulation_2_barges_custom_env):
    """Test get_critical_path_df method in a 2 barge simulation."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 79, "79 critical activities expected"


def test_get_critical_path_df_simple_simulation(simulation_while_sequential):
    """Test get_critical_path_df method in simulation with a single while-activity."""
    my_cp = DependenciesFromSimpy(**simulation_while_sequential)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 149, "149 critical activities expected"


def test_get_critical_path_df_storm(simulation_2_barges_custom_env_storm):
    """Test get_critical_path_df method in 2 barge simulation with weather delay."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env_storm)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 82, "82 critical activities expected"


def test_get_critical_path_with_startevent(simulation_2_barges_custom_env_start):
    """Test get_critical_path_df method in 2 barge simulation with start wait."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env_start)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 80, "80 critical dependencies expected"
