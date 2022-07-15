"""
test for module core.superlog.py

python -m pytest tests/test_superlog.py --cov=superlog.py
"""
import os

import pandas as pd

# module to be tested
import openclsim.plot.superlog as cp

# import some code to run simulation
from .data.demo_simulation import run_simulation

data_path = os.path.join(os.path.dirname(__file__), "data")


def test_init():
    """test init"""
    my_log = cp.SuperLog(pd.read_excel(os.path.join(data_path, "super_log.xlsx")))
    assert isinstance(my_log, cp.SuperLog), "instance SuperLog expected"


def test_dependencies():
    """test dependencies"""
    my_log = cp.SuperLog(pd.read_excel(os.path.join(data_path, "super_log.xlsx")))
    assert len(my_log.dependencies) == 113, "113 dependencies expected"
    for some_tuple in [
        ("cp_activity_1", "cp_activity_2"),
        ("cp_activity_106", "cp_activity_2"),
        ("cp_activity_2", "cp_activity_44"),
        ("cp_activity_45", "cp_activity_24"),
        ("cp_activity_24", "cp_activity_34"),
    ]:
        assert (
            some_tuple in my_log.dependencies
        ), f"specific dependency missing {some_tuple}"


def test_plot():
    """test making of plot"""
    my_log = cp.SuperLog(pd.read_excel(os.path.join(data_path, "super_log.xlsx")))
    fig, ax = my_log.make_gantt_mpl()
    assert len(ax.get_legend().texts) == 21, "legend with 21 entries expected"
    assert len(ax.get_yticks()) == 6, "6 yticks expected"

    # completely not true, but just add this column and tesplot with black asterix
    my_log.df_super_log.loc[:, "is_critical"] = True
    fig, ax = my_log.make_gantt_mpl()
    assert len(ax.get_legend().texts) == 21, "legend with 21 entries expected"
    assert len(ax.get_yticks()) == 6, "6 yticks expected"


def test_from_objects():
    """test from objects"""
    dict_objects_simulation = run_simulation(2, 100)
    list_objects_with_log = list(dict_objects_simulation["vessels"].values()) + [
        dict_objects_simulation["from_site"],
        dict_objects_simulation["to_site"],
        dict_objects_simulation["to_site2"],
    ]
    my_log = cp.SuperLog.from_objects(
        list_objects_with_log,
        id_map=list(dict_objects_simulation["activities"].values()),
    )
    # my_combi = cp.combine_logs(list_objects_with_log, id_map=list(dict_objects_simulation['activities'].values()))
    # my_superlog = cp.reshape_superlog(my_combi)
    # my_log_with_cp = cp.add_unique_activity(my_superlog)
    assert len(my_log.dependencies) == 113, "113 dependencies expected"
    for some_tuple in [
        ("cp_activity_3", "cp_activity_45"),
        ("cp_activity_13", "cp_activity_55"),
        ("cp_activity_45", "cp_activity_24"),
    ]:
        assert (
            some_tuple in my_log.dependencies
        ), f"specific dependency missing {some_tuple}"
