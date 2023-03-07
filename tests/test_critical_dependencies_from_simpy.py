"""
Tests for openclsim.critical_path.dependencies_from_simpy module
"""
import datetime as dt

from openclsim.critical_path.dependencies_from_simpy_step import (
    MyCustomSimpyEnv,
    DependenciesFromSimpy,
)

from tests.conftest import demo_data
simulation_2_barges_custom_env = demo_data(2, 100, MyCustomSimpyEnv)
simulation_4_barges_custom_env = demo_data(4, 100, MyCustomSimpyEnv)


def test_get_dependency_list(simulation_2_barges_custom_env):
    """ Test get_dependency_list method."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    dependency_list = my_cp.get_dependency_list()

    assert len(dependency_list) == 103, "103 dependencies expected"

    # check that all dependencies have zero time diff
    for dep in my_cp.dependency_list:
        t0 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[0]), 'end_time'].iloc[0]
        t1 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[1]), 'start_time'].iloc[0]
        assert t1-t0 == dt.timedelta(seconds=0), "dependencies have no len in time!"


def test_get_critical_path_df(simulation_2_barges_custom_env):
    """ Test get_critical_path_df method. """
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 79, "79 critical activities expected"


def temp_visualisation():
    from openclsim.plot.vessel_planning import get_gantt_chart
    import plotly.graph_objs as go
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    critical_df = my_cp.get_critical_path_df()
    data = get_gantt_chart(simulation_2_barges_custom_env['object_list'],
                           id_map=simulation_2_barges_custom_env['activity_list'],
                           static=True, critical_path_dataframe=critical_df)
    fig = go.Figure(**data)
    fig.show()
    fig.write_html(r"D:\temp_files\crit1_2barges.html")

    my_cp = DependenciesFromSimpy(**simulation_4_barges_custom_env)
    critical_df = my_cp.get_critical_path_df()
    data = get_gantt_chart(simulation_4_barges_custom_env['object_list'],
                           id_map=simulation_4_barges_custom_env['activity_list'],
                           static=True, critical_path_dataframe=critical_df)
    fig = go.Figure(**data)
    fig.show()
    fig.write_html(r"D:\temp_files\crit1_4barges.html")


