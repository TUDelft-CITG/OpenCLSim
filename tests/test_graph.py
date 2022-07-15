"""
test for module core.graph.py

python -m pytest tests/test_graph.py --cov=graph.py
"""
import os

import pandas as pd
import pytest

# module to be tested
import openclsim.plot.graph as cg
import openclsim.plot.superlog as cp

# %% data
data_path = os.path.join(os.path.dirname(__file__), 'data')

# %% fixtures


@pytest.fixture()
def super_log():
    """superlog and dependencies for testing"""
    my_log = cp.SuperLog(
        pd.read_excel(os.path.join(data_path, "super_log.xlsx"))
    )

    return my_log.df_super_log.drop(columns=['Unnamed: 0'])


@pytest.fixture()
def dependencies():
    """superlog and dependencies for testing"""
    my_log = cp.SuperLog(
        pd.read_excel(os.path.join(data_path, "super_log.xlsx"))
    )

    return my_log.dependencies

# %% tests


def test_init(super_log, dependencies):
    """ test init """
    my_graph = cg.ActivityGraph(super_log, dependencies)
    assert isinstance(my_graph, cg.ActivityGraph), (
        "instance ActivityGraph expected"
    )


def test_path_finder(super_log, dependencies):
    """ test finding a path """
    my_graph = cg.ActivityGraph(super_log, dependencies)
    list_critical = my_graph.mark_critical_activities()
    assert isinstance(list_critical, list), (
        "instance of list expected"
    )
    assert len(list_critical) == 102, "expected 102 critical activities"
