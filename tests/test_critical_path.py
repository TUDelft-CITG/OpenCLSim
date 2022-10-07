"""Testing plot/critical_path.py"""
import os

import pandas as pd
import pytest

# module to be tested
from openclsim.plot.critical_path import CpLog
from openclsim.plot.vessel_planning import get_gantt_chart

from .data.demo_simulation import run_simulation

# %% data


data_path = os.path.join(os.path.dirname(__file__), "data")


# %% fixtures


@pytest.fixture()
def demo_simulation():
    """Generate a simulation."""
    return run_simulation(nt_barges=3, total_amount=1000)


@pytest.fixture()
def objs_and_acts(demo_simulation):
    """CpLog for testing."""
    sim_dict = demo_simulation
    my_objects = list(sim_dict["vessels"].values()) + [
        sim_dict["from_site"],
        sim_dict["to_site"],
        sim_dict["to_site2"],
    ]
    my_activities = list(sim_dict["activities"].values())

    return my_objects, my_activities


# %% testing


def test_init_cplog(objs_and_acts):
    """Testing init of a CpLog"""
    my_objects, my_activities = objs_and_acts

    my_log = CpLog(list_objects=my_objects, list_activities=my_activities)

    assert isinstance(my_log, CpLog)


def test_dependencies_log(objs_and_acts):
    """Testing dependencies"""
    my_objects, my_activities = objs_and_acts

    my_log = CpLog(list_objects=my_objects, list_activities=my_activities)

    dep_log = my_log.get_dependencies_log_based()
    assert isinstance(dep_log, list)
    assert len(dep_log) == 1134


def test_dependencies_model(objs_and_acts):
    """Testing dependencies"""
    my_objects, my_activities = objs_and_acts

    my_log = CpLog(list_objects=my_objects, list_activities=my_activities)

    dep_model = my_log.get_dependencies_model_based()
    assert isinstance(dep_model, list)
    assert len(dep_model) == 1002


def test_critical(objs_and_acts):
    """Testing the marking of critical activities"""
    my_objects, my_activities = objs_and_acts

    my_log = CpLog(list_objects=my_objects, list_activities=my_activities)

    dep_log = my_log.get_dependencies_log_based()

    df = my_log.mark_critical_activities(dep_log)

    assert isinstance(df, pd.DataFrame)


def test_plot(objs_and_acts):
    """Testing the plotting of critical activities"""
    my_objects = objs_and_acts[0]
    my_activities = objs_and_acts[1]

    my_log = CpLog(list_objects=my_objects, list_activities=my_activities)

    dep_log = my_log.get_dependencies_log_based()
    df = my_log.mark_critical_activities(dep_log)

    _ = get_gantt_chart(my_objects, critical_path=df)
