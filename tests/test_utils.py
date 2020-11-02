"""Util functions for the tests."""


def parse_log(log):
    """Parse the log into benchmarkable data."""
    new_log = log.copy()

    for state in new_log["ObjectState"]:
        if "geometry" in state.keys():
            x, y = state["geometry"].xy
            state["geometry"] = x[0], y[0]

    return new_log
