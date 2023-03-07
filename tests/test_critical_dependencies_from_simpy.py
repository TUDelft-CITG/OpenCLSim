"""
Tests for openclsim.critical_path.dependencies_from_simpy module
"""
from openclsim.critical_path.dependencies_from_simpy_step import (
    MyCustomSimpyEnv,
    DependenciesFromSimpy,
)

from tests.conftest import demo_data
simulation_2_barges_custom_env = demo_data(2, 100, MyCustomSimpyEnv)


def test_init(simulation_2_barges_custom_env):
    """Test initialisation."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    dependency_list = my_cp.get_dependency_list()
    assert len(dependency_list) == 103, "103 dependencies expected"


def temp_visualisation():
    from openclsim.plot.vessel_planning import get_gantt_chart
    import plotly.graph_objs as go
    data = get_gantt_chart(simulation_2_barges_custom_env['object_list'], static=True)
    fig = go.Figure(**data)
    fig.show()
    fig.write_html(r"D:\temp_files\crit1.html")
