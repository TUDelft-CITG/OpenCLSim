"""Util functions for the tests."""

import numpy as np
import pandas as pd

import openclsim.utils


def assert_log(simulation_object):
    """Parse the new_log into benchmarkable data."""
    new_log = simulation_object.log.copy()
    length = len(new_log["Timestamp"])
    df = pd.DataFrame(new_log)
    df["Timestamp"] = df["Timestamp"].view(np.int64)

    assert isinstance(new_log["Timestamp"], list)
    assert isinstance(new_log["ActivityID"], list)
    assert isinstance(new_log["ActivityState"], list)
    assert isinstance(new_log["ObjectState"], list)
    assert isinstance(new_log["ActivityLabel"], list)

    assert len(new_log["Timestamp"]) == length
    assert len(new_log["ActivityID"]) == length
    assert len(new_log["ActivityState"]) == length
    assert len(new_log["ObjectState"]) == length
    assert len(new_log["ActivityLabel"]) == length

    assert len(df[df["ActivityState"] == "START"]) == len(
        df[df["ActivityState"] == "STOP"]
    )
    assert len(df[df["ActivityState"] == "WAIT_START"]) == len(
        df[df["ActivityState"] == "WAIT_STOP"]
    )
    assert all(
        df[
            (df["ActivityState"] != "WAIT_START")
            & (df["ActivityState"] != "WAIT_STOP")
            & (df["ActivityState"] != "START")
            & (df["ActivityState"] != "STOP")
        ]
        == "UNKNOWN"
    )

    assert all(
        np.array(df[df["ActivityState"] == "STOP"]["Timestamp"])
        - np.array(df[df["ActivityState"] == "START"]["Timestamp"])
        >= 0
    )
    assert all(
        np.array(df[df["ActivityState"] == "WAIT_STOP"]["Timestamp"])
        - np.array(df[df["ActivityState"] == "WAIT_START"]["Timestamp"])
        >= 0
    )

    for state in new_log["ObjectState"]:
        if "geometry" in state.keys():
            x, y = state["geometry"].xy
            state["geometry"] = x[0], y[0]

    str_df = df.astype(str)
    cols = list(str_df.keys())
    str_df["count"] = str_df.groupby(cols)[cols[0]].transform("size")
    str_df = str_df.drop_duplicates().reset_index(drop=True).fillna(1.0)
    assert all(str_df["count"] == 1)

    for sub_process in getattr(simulation_object, "sub_processes", []):
        assert_log(sub_process)

    return new_log


def test_notebook_path():
    """test if we can find the notebook path"""
    notebook_path = openclsim.utils.find_notebook_path()
    assert "notebook" in str(notebook_path), "notebook should be in the notebook path"
