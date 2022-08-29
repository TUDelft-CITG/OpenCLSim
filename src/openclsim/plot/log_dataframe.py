"""Get the log of the simulation objects in a pandas dataframe."""

import pandas as pd

from openclsim.model import get_subprocesses
from openclsim.plot.graph_dependencies import DependencyGraph


def get_log_dataframe(simulation_object, id_map=None):
    """Get the log of the simulation objects in a pandas dataframe.

    Parameters
    ----------
    simulation_object
        object from which the log is returned as a dataframe sorted by "Timestamp"
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list of top-activities of which also all sub-activities
          will be resolved, e.g.: [while_activity]
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}
    """
    if id_map is None:
        id_map = []

    if isinstance(id_map, list):
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


def get_log_dataframe_activity(activity, keep_only_base=True):
    """Get the log of the activity object in a pandas dataframe.

    Parameters
    ----------
    activity : object
        object from which the log is returned as a dataframe sorted by "Timestamp"
    keep_only_base : boolean
        if True (default) only the base (containing no sub_processes) activities are kept in pd.DataFrame output
    """

    list_all_activities = get_subprocesses(activity)
    id_map = {act.id: act.name for act in list_all_activities}

    df_all = pd.DataFrame()
    for sub_activity in list_all_activities:

        df = (
            pd.DataFrame(sub_activity.log)
                .sort_values(by=["Timestamp"])
                .sort_values(by=["Timestamp"])
        )

        df_concat = pd.concat(
            [
                df.filter(items=["ActivityID"]),
                pd.DataFrame(sub_activity.log).filter(["Timestamp", "ActivityState"]),
                pd.DataFrame(sub_activity.log["ObjectState"]),
            ],
            axis=1,
        )

        df_all = pd.concat([df_all, df_concat], axis=0)
        df_all.loc[:, "Activity"] = df_all.loc[:, "ActivityID"].replace(id_map)

    if keep_only_base:
        # filter out all non-base activities
        my_graph = DependencyGraph([activity])
        df_all = df_all.loc[df_all.loc[:, "ActivityID"].isin(my_graph.getListBaseActivities()), :]

    return df_all
