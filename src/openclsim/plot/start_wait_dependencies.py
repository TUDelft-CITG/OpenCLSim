"""
This module contains functions
 - to get activities with start event condition
 - to get activity dependencies based on start event condition
 - to get critical path dependencies surrounding critical path activities with state 'WAITING'
"""
import logging

from openclsim.model.shift_amount_activity import ShiftAmountActivity
from openclsim.plot.graph_dependencies import is_basic_activity
from openclsim.plot.log_dataframe import get_subprocesses


def get_start_events(acts):
    """
    this function gets all base activities with single start event condition

    Parameters
    ------------
    acts : list
        main activity or list of main activities (after simulation)

    Returns
    ----------
    list_start_dependencies : list
        list of start_event dictionairies, enriched with activity id which has this start event as attribute
    """
    list_all_base_activities = [
        a for a in get_subprocesses(acts) if is_basic_activity(a)
    ]
    list_start_dependencies = []
    for ba in list_all_base_activities:
        if ba.start_event is not None and len(ba.start_event) == 1:
            dict_start_event = ba.start_event[0]
            dict_start_event["activity_id"] = ba.id
            list_start_dependencies.append(dict_start_event)
    return list_start_dependencies


def get_act_dependencies_start(acts):
    """
    get activity dependencies based on start event conditions.
    For now only 'container' type supported for base activities.

    Parameters
    ------------
    acts : list
        main activity or list of main activities (after simulation)

    Returns
    ----------
    list_act_dependencies_start : list
        list of dependencies (tuples with activity ids)
    """
    list_start_dependencies = get_start_events(acts)
    # now see which base activities deal with container level
    list_all_base_activities = [
        a for a in get_subprocesses(acts) if is_basic_activity(a)
    ]
    list_act_dependencies_start = []
    for start_dependency in list_start_dependencies:
        if start_dependency["type"] == "container":
            # dependency on all ShiftAmount Activities with destination as in start_dependency
            dependent_on = [
                a
                for a in list_all_base_activities
                if issubclass(type(a), ShiftAmountActivity)
                and a.destination == start_dependency["concept"]
            ]
            for dep in dependent_on:
                list_act_dependencies_start.append(
                    (dep.id, start_dependency["activity_id"])
                )
        else:
            logging.warning(
                f"Finding dependencies for start condition type"
                f" {start_dependency['type']} not (yet) supported"
            )
    return list_act_dependencies_start


def get_wait_dependencies_cp(df_log_cp):
    """
    get wait dependencies - by definition a 'wait' is (ALSO) dependent on itself.
    So we need the critcal path log (dataframe) in order to determine these as well as the activity dependencies

    Parameters
    -----------
    df_log_cp : pd.DataFrame
        the dataframe within object of class CpLog (plot.critical_path_log.py)

    Returns
    --------
    list_wait_dependencies : list
        a list of dependencies (tuples with cp_Aativity_id values)
    """
    list_wait_dependencies = []
    bool_is_wait = df_log_cp.loc[:, "state"] == "WAITING"
    if bool_is_wait.any():
        for idx, row in df_log_cp.loc[bool_is_wait, :].iterrows():
            list_ids_before = df_log_cp.loc[
                (df_log_cp.loc[:, "ActivityID"] == row.loc["ActivityID"])
                & (df_log_cp.loc[:, "end_time"] == row.loc["start_time"]),
                "cp_activity_id",
            ].tolist()
            list_ids_after = df_log_cp.loc[
                (df_log_cp.loc[:, "ActivityID"] == row.loc["ActivityID"])
                & (df_log_cp.loc[:, "start_time"] == row.loc["end_time"]),
                "cp_activity_id",
            ].tolist()
            # by default only 1 activity with same activity ID before/after wait, so no explicit check - grab element 0
            if len(list_ids_before) > 0:
                list_wait_dependencies.append(
                    (list_ids_before[0], row.loc["cp_activity_id"])
                )
            if len(list_ids_after) > 0:
                list_wait_dependencies.append(
                    (row.loc["cp_activity_id"], list_ids_after[0])
                )
    else:
        logging.info("No waiting activity in this critical path log")

    return list_wait_dependencies
