"""Util functions for the tests."""


def parse_log(log):
    """Parse the log into benchmarkable data."""
    new_log = log.copy()
    new_log["Geometry"] = [
        (L.x, L.y) if L is not None else None for L in log["Geometry"]
    ]
    return new_log
