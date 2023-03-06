"""Get the log of the simulation objects in a pandas dataframe."""

import pandas as pd

from openclsim.model import get_subprocesses


def get_log_dataframe(simulation_object, id_map=None):
    """Get the chronological log of the simulation objects in a pandas dataframe.

    result is sorted by Timestamp

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

    if isinstance(id_map, dict):
        id_map = [*id_map.values()]    
    if isinstance(id_map, list):
        id_map = {act.id: act.name for act in get_subprocesses(id_map)} # needs to be recursive: flatten
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

def get_ranges_dataframe(simulation_object, id_map=None):
    """Get the chronological ranges of the simulation objects in a pandas dataframe.

    Turns a log of length (2*n) of START, STOP events at t=Timestamp into
    a log of length (n) of ranges between t=[TimestampStart, TimestampStop]
    
    result is sorted by Timestamp

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
    
    idkey='Activity' # ActivityID
    
    li = []
    
    # do this analysis per ActivityID
    # each intervals has START STOP
    # at most 1 interval may be without STOP, the last one
    
    for ActivityID in set(log[idkey]):

        log1 = log[log[idkey]==ActivityID]

        t0 = log1[log1['ActivityState']=='START'].rename(columns={'Timestamp':'TimestampStart'})
        t1 = log1[log1['ActivityState']=='STOP'].rename(columns={'Timestamp':'TimestampStop'})
        
        # add geometry?
        if 'container level' in log1.keys():
            t0 = t0[['TimestampStart','container level']].rename(columns={'container level':'ContainerLevelStart'})
            t1 = t1[['TimestampStop','container level']].rename(columns={'container level':'ContainerLevelStop'})
        else:
            t0 = t0[['TimestampStart']]
            t1 = t1[['TimestampStop']]
        
        t0['trip'] = range(1,len(t0)+1)
        t1['trip'] = range(1,len(t1)+1)
        
        if len(t0)==len(t1):
            pass
        elif len(t0)==len(t1)+1:
            print('END missing')
            dt1 = pd.DataFrame.from_dict({'trip':[len(t0)],'TimestampStop':[None]}) # will give NaT
            t1 = pd.concat([t1, dt1], ignore_index=True)
        else:
            raise Exception('At most 1 range may be without STOP')
        s = t0.merge(t1, on='trip')
        
        s[idkey] = ActivityID
        s['TimestampDt'] = s['TimestampStop'] - s['TimestampStart']
        li.append(s)
        
    R = pd.concat(li)
    R = R.sort_values(by=["TimestampStart"])
        
    return R
