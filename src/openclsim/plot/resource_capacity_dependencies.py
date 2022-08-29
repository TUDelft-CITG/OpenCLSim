"""
Module with main function 'get_resource_capacity_dependencies'.
"""
import pandas as pd

import openclsim.core as core


def get_resource_capacity_dependencies(cp_log, list_objects):
    """
    given a critical path log and a list of objects this function loops
    over the objects and creates critical path dependencies for activities which seem
    to be waiting on utilisation of resource which is capped at certain capacity

    Parameters
    ------------
    cp_log : pd.DataFrame
        pd.DataFrame as within CpLog (plot.critical_path_log.py)
    list_objects : list
        list of all simulation objects (after simulation, e.g. [vessel, site, etc]
    """

    # step 1: get all objects for which a resource limitation is applicable
    objs_with_resource = [
        obj for obj in list_objects if check_resource(obj) is not None
    ]

    # init output
    list_dependencies_cp_all = []
    # step 2: see what is going on at one of the resource sites
    for obj_resource in objs_with_resource:
        nr_resources = check_resource(obj_resource)
        resource_log = get_timebased_overview_resource(cp_log, obj_resource.name)

        # now simply mark activies where utility > capacity and doublecheck that at this (start) time others end
        bool_greater_than_cap = (resource_log.loc[:, "utility"] > nr_resources) & (
            resource_log.loc[:, "event"] == "START"
        )
        list_dependencies_cp = []
        for idx in bool_greater_than_cap.loc[bool_greater_than_cap].index.values:
            # is this one really waiting, i.e. is there a gap  looking at other simulation object (vessel)
            shared_simulation_objects = list(
                set(
                    cp_log.loc[
                        cp_log.loc[:, "cp_activity_id"]
                        == resource_log.loc[idx, "cp_activity_id"],
                        "SimulationObject",
                    ]
                )
                - {obj_resource.name}
            )
            if len(shared_simulation_objects) == 0:
                # no new dependencies to make, no shared simulation objects for this activity:
                # dependencies solely defined by activities
                continue
            elif len(shared_simulation_objects) == 1:
                shared_simulation_object = shared_simulation_objects[0]
            else:
                raise ValueError(
                    "This function can only handle simple activities sharing 1 site and 1 vessel"
                )

            # so at this point we learn whether the shared object has a gap or not.
            # If gap (no identical end times), then continue
            bool_any_endings_now = (
                cp_log.loc[:, "SimulationObject"] == shared_simulation_object
            ) & (cp_log.loc[:, "end_time"] == resource_log.loc[idx, "datetime"])
            # noinspection PyUnresolvedReferences
            if sum(bool_any_endings_now) == 0:
                # what is stopping now (so that this one can start)
                bool_stopping_now = (resource_log.loc[:, "event"] == "STOP") & (
                    resource_log.loc[:, "datetime"] == resource_log.loc[idx, "datetime"]
                )
                activities_stopping_now = resource_log.loc[
                    bool_stopping_now, "cp_activity_id"
                ].tolist()
                for act in activities_stopping_now:
                    list_dependencies_cp.append(
                        (act, resource_log.loc[idx, "cp_activity_id"])
                    )

        list_dependencies_cp_all = list_dependencies_cp_all + list_dependencies_cp

    return list_dependencies_cp_all


# %% aux fcns
def check_resource(obj):
    """WIP check if an object has a resource"""
    if issubclass(type(obj), core.HasResource):
        return obj.resource.capacity
    else:
        return None


def get_timebased_overview_resource(df_log, name_simulation_object):
    """get a df with all activities as start/stop for certain resource (simulation) object"""
    bool_corresponding_to_object = df_log["SimulationObject"] == name_simulation_object
    # include WAIT as well
    activity_ids = df_log.loc[bool_corresponding_to_object, "ActivityID"].tolist()
    keep = (df_log.loc[:, "ActivityID"].isin(activity_ids)) & (
        df_log.loc[:, "SimulationObject"].isin([name_simulation_object, "Activity"])
    )
    resource_log_cp = df_log.loc[keep, :]

    # make a log of how many resources are used
    # START ==> take one resource
    # STOP ==> release one resource
    all_starts = pd.DataFrame(
        {
            "datetime": resource_log_cp["start_time"],
            "event": "START",
            "cp_activity_id": resource_log_cp["cp_activity_id"],
        }
    )
    all_stops = pd.DataFrame(
        {
            "datetime": resource_log_cp["end_time"],
            "event": "STOP",
            "cp_activity_id": resource_log_cp["cp_activity_id"],
        }
    )
    resource_log = pd.concat([all_starts, all_stops])
    # START always before stop (sedcondary ordering when same time)
    resource_log = resource_log.sort_values(["datetime", "event"]).reset_index(
        drop=True
    )

    # first add resource utility level
    resource_log.loc[:, "utility"] = None
    ut_current = 0
    for idx, row in resource_log.iterrows():
        if row.loc["event"] == "START":
            ut_current += 1
        if row.loc["event"] == "STOP":
            ut_current -= 1
        resource_log.loc[idx, "utility"] = ut_current
    return resource_log
