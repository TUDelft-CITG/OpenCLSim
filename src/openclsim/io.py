import pandas as pd

from openclsim.plot import get_log_dataframe


def get_tree_as_list(treelist, depth=0) -> dict:
    """recursively flatten a tree of activities into dict of lists.

    Returns a dict with fields:
    ActivityID, ActivityName, activity,
    ParentId, ParentName, ParentLevel

    The tree can be reconstructed from the Parent relations.

    Example:
        get_tree_as_list(activities)['activity']

    Parameters
    ----------
    treelist
        one activity, or list or dict with activities
    depth
        depth level of top of hierarchy (default 0)

    Returns
    --------
    activity_dict : dict
        a dict with fields
           ActivityID,   ActivityClass,ActivityName,
           ParentId,ParentName,ParentLevel,
           activity

    """

    if isinstance(treelist, list):
        pass
    elif isinstance(treelist, dict):
        treelist = [*treelist.values()]
    else:
        treelist = [treelist]

    activity = [x for x in treelist]
    ActivityID = [x.id for x in treelist]
    ActivityName = [x.name for x in treelist]
    ActivityClass = [type(x).__name__ for x in treelist]
    ParentId = [
        None,
    ] * len(ActivityID)
    ParentName = [
        "",
    ] * len(ActivityID)
    ParentLevel = [
        depth,
    ] * len(ActivityID)

    for i, act in enumerate(treelist):
        if hasattr(act, "sub_processes"):
            d = get_tree_as_list(act.sub_processes, depth + 1)
            ActivityID += d["ActivityID"]
            activity += d["activity"]
            ParentId += [act.id] * len(d["activity"])
            ParentName += [act.name] * len(d["ParentName"])
            ActivityClass += d["ActivityClass"]
            ActivityName += d["ActivityName"]
            ParentLevel += d["ParentLevel"]

    return {
        "ActivityID": ActivityID,
        "ActivityName": ActivityName,
        "ActivityClass": ActivityClass,
        "ParentId": ParentId,
        "ParentName": ParentName,
        "ParentLevel": ParentLevel,
        "activity": activity,
    }


def get_activity_resources(activities, ofile=None):
    """Extract the resources assigned to an activity to a resolved list

    Note these are just the model-defined activities and the
    mover, processor, origin and destination relations
    without the log. activities thasty have no concept assigned
    to it, are not exported. Use export_activities() for that.

    Note that 1 acticvity can have multiple concepts assigned
    to it simultaneously.

    returned keys are
            'ActivityID','ActivityName','ActivityClass',
            'ConceptID','ConceptName','ConceptMode'

    Parameters
    ----------
    activities
        hierarchical activities to be resolved and stored
    concept_name
        optional filter the flattened list for one
        concept_name (Sites and Vessels). Default: None
    ofile
        name of a csv file to which to export the list (optional)
    """

    df = pd.DataFrame(get_tree_as_list(activities))

    li = []
    for attr_name in ["processor", "mover", "origin", "destination"]:
        mask = [hasattr(x, attr_name) for x in df["activity"]]
        li += [
            (
                x.id,
                x.name,
                type(x).__name__,
                getattr(getattr(x, attr_name), "id"),
                getattr(getattr(x, attr_name), "name"),
                attr_name,
            )
            for x in df[mask]["activity"]
        ]
    tmp = list(zip(*li))
    res = pd.DataFrame.from_dict(
        {
            "ActivityID": tmp[0],
            "ActivityName": tmp[1],
            "ActivityClass": tmp[2],
            "ConceptID": tmp[3],
            "ConceptName": tmp[4],
            "ConceptMode": tmp[5],
        }
    )

    if ofile:
        res.to_csv(ofile, index=False)

    return res


def get_ranges_dataframe(simulation_object, id_map=None):
    """Get the chronological ranges of one simulation object in a pandas dataframe.

    Turns a log of length (2*n) of START, STOP events at t=Timestamp into
    a log of length (n) of ranges between t=[TimestampStart, TimestampStop]

    The result is sorted by Timestamp

    Parameters
    ----------
    simulation_object
        object from which the log is returned as a dataframe sorted by "Timestamp"
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list or dict of concepts
        * a manual id_map to resolve concept uuids to labels, e.g. {'uuid1':'vessel A'}
    """

    log = get_log_dataframe(simulation_object, id_map=id_map)

    idkey = "Activity"  # ActivityID

    li = []

    # do this analysis per ActivityID
    # each intervals has START STOP
    # at most 1 interval may be without STOP, the last one

    for ActivityID in set(log[idkey]):
        log1 = log[log[idkey] == ActivityID]

        t0 = log1[log1["ActivityState"] == "START"].rename(
            columns={"Timestamp": "TimestampStart"}
        )
        t1 = log1[log1["ActivityState"] == "STOP"].rename(
            columns={"Timestamp": "TimestampStop"}
        )

        # add geometry?
        if "container level" in log1.keys():
            t0 = t0[["TimestampStart", "container level"]].rename(
                columns={"container level": "ContainerLevelStart"}
            )
            t1 = t1[["TimestampStop", "container level"]].rename(
                columns={"container level": "ContainerLevelStop"}
            )
        else:
            t0 = t0[["TimestampStart"]]
            t1 = t1[["TimestampStop"]]

        t0["trip"] = range(1, len(t0) + 1)
        t1["trip"] = range(1, len(t1) + 1)

        if len(t0) == len(t1):
            pass
        elif len(t0) == len(t1) + 1:
            print("END missing")
            dt1 = pd.DataFrame.from_dict(
                {"trip": [len(t0)], "TimestampStop": [None]}
            )  # will give NaT
            t1 = pd.concat([t1, dt1], ignore_index=True)
        else:
            raise Exception("At most 1 range may be without STOP")
        s = t0.merge(t1, on="trip")

        s[idkey] = ActivityID
        dt = s["TimestampStop"] - s["TimestampStart"]
        # powerbi gannt can only handle integer durations. so use a small unit:sec
        s["TimestampDt"] = [x.total_seconds() for x in dt]
        li.append(s)

    R = pd.concat(li)
    R = R.sort_values(by=["TimestampStart"])

    return R


def get_concepts(
    concepts,
    namespace="",
    ofile=None,
):
    """Save the concepts vities to a resolved csv file

    Concepts can be stored in 1 file (Sites and Vessels)
    or they can  be stored mixed together.

    Parameters
    ----------
    concepts
        concepts to be resolved and stored
    namespace
        str that will prepad the column names 'Name', 'ID', "Class".
        e.g. Vessel, Site or Concept
    ofile
        name of csv file to be exported
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list or dict of concepts
        * a manual id_map to resolve concept uuids to labels, e.g. {'uuid1':'vessel A'}
    """

    if isinstance(concepts, dict):
        concepts = [*concepts.values()]

    df = {
        f"{namespace}Name": [x.name for x in concepts],
        f"{namespace}ID": [x.id for x in concepts],
        f"{namespace}Class": [type(x).__name__ for x in concepts],
    }

    df = pd.DataFrame(df)
    if ofile:
        df.to_csv(ofile, index=False)

    return df


def get_activities(activities, ofile=None):
    """Save the activities tree to a resolved list in a csv file

    Note these are just the model-defined activities and the
    mover, processor, origin and destination relations
    without the log.

    returned keys are
            'ActivityID','ActivityName','ActivityClass',
            'ParentId','ParentName','ParentLevel',
            'OriginID','OriginName',
            'DestinationID','DestinationName',
            'ProcessorID','ProcessorName',
            'MoverID', 'MoverName'

    Parameters
    ----------
    activities
        hierarchical activities to be resolved and stored
    ofile
        name of csv file to be exported
    """

    df = pd.DataFrame(get_tree_as_list(activities))

    processor = [
        x.processor if hasattr(x, "processor") else None for x in df["activity"]
    ]
    mover = [x.mover if hasattr(x, "mover") else None for x in df["activity"]]
    origin = [x.origin if hasattr(x, "origin") else None for x in df["activity"]]
    destination = [
        x.destination if hasattr(x, "destination") else None for x in df["activity"]
    ]

    df["ProcessorID"] = [x.id if x else None for x in processor]
    df["MoverID"] = [x.id if x else None for x in mover]
    df["OriginID"] = [x.id if x else None for x in origin]
    df["DestinationID"] = [x.id if x else None for x in destination]

    df["ProcessorName"] = [x.name if x else "" for x in processor]
    df["MoverName"] = [x.name if x else "" for x in mover]
    df["OriginName"] = [x.name if x else "" for x in origin]
    df["DestinationName"] = [x.name if x else "" for x in destination]

    # manually set column order + exclude actual 'activity' object !

    keys = [
        "ActivityID",
        "ActivityName",
        "ActivityClass",
        "ParentId",
        "ParentName",
        "ParentLevel",
        "OriginID",
        "OriginName",
        "DestinationID",
        "DestinationName",
        "ProcessorID",
        "ProcessorName",
        "MoverID",
        "MoverName",
    ]

    df = pd.DataFrame(df)

    if ofile:
        df.to_csv(ofile, columns=keys, index=False)

    return df


def get_activity_log(activities, ofile=None):
    """Save log of activities to a resolved start-stop list in a csv file

    This export of the logged time ranges can be used to plot Gannt
    charts in for instance Qlik and PowerBI. Load the coupled export_activities()
    file to resolve the Activty properties and relations to (Sites and Vessels).


    Parameters
    ----------
    activities
        hierarchical activities to be resolved and stored
    ofile
        name of csv file to be exported
    """

    df = pd.DataFrame(get_tree_as_list(activities))

    li = []
    for i, rowi in df.iterrows():
        log = get_ranges_dataframe(rowi["activity"])
        log.rename(columns={"Activity": "ActivityID"}, inplace=True)
        li.append(log)
    ActivityRanges = pd.concat(li)

    ActivityRanges = ActivityRanges.merge(
        df[["ActivityID", "ActivityName", "ActivityClass"]], on="ActivityID", how="left"
    )

    keys = [
        "trip",
        "ActivityID",
        "ActivityName",
        "ActivityClass",
        "TimestampStart",
        "TimestampStop",
        "TimestampDt",
    ]

    if ofile:
        ActivityRanges.to_csv(ofile, columns=keys, index=False)

    return ActivityRanges.sort_values(by=["TimestampStart"])
