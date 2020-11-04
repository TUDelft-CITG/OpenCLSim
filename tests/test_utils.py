"""Util functions for the tests."""
import pandas as pd


def test_log(log):
    """Parse the new_log into benchmarkable data."""
    new_log = log.copy()
    length = len(new_log["Timestamp"])

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

    df = pd.DataFrame(log).filter(["ActivityState"])

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

    for state in new_log["ObjectState"]:
        if "geometry" in state.keys():
            x, y = state["geometry"].xy
            state["geometry"] = x[0], y[0]

    return new_log
