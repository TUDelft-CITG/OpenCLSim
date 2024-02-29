"""Get the log of the simulation objects in a pandas dataframe."""

import pandas as pd

from openclsim.model import get_subprocesses


def get_log_dataframe(simulation_object, id_map=None):
    """Get the chronological log of one simulation object in a pandas dataframe.

    result is sorted by Timestamp

    Parameters
    ----------
    simulation_object
        object from which the log is returned as a dataframe sorted by "Timestamp"
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list or dict of top-activities of which also all sub-activities
          will be resolved, e.g.: [while_activity]
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}
    """
    if id_map is None:
        id_map = []

    if isinstance(id_map, dict):
        id_map = [*id_map.values()]
    if isinstance(id_map, list):
        # TO DO should in fact be recursive for nested activities
        id_map = {act.id: act.name for act in get_subprocesses(id_map)}
    else:
        id_map = id_map if id_map else {}

    df = (
        pd.DataFrame(simulation_object.log)
        .sort_values(by=["Timestamp"])
        .sort_values(by=["Timestamp"])
    )
    return pd.concat(
        [
            (
                df.filter(items=["ActivityID"])
                .rename(columns={"ActivityID": "Activity"})
                .replace(id_map)
            ),
            pd.DataFrame(simulation_object.log).filter(["Timestamp", "ActivityState"]),
            pd.DataFrame(simulation_object.log["ObjectState"]),
            pd.DataFrame(simulation_object.log["ActivityLabel"]),
        ],
        axis=1,
    )
