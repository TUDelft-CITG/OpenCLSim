import pathlib

import pandas as pd

import openclsim


def find_src_path():
    """Lookup the path where the package are located. Returns a pathlib.Path object."""
    openclsim_path = pathlib.Path(openclsim.__file__)
    # check if the path looks normal
    assert "openclsim" in str(
        openclsim_path
    ), "we can't find the openclsim path: {openclsim_path} (openclsim not in path name)"
    # src_dir/openclsim/__init__.py -> ../.. -> src_dir
    src_path = openclsim_path.parent.parent
    return src_path


def find_notebook_path():
    """Lookup the path where the notebooks are located. Returns a pathlib.Path object."""
    src_path = find_src_path()
    notebook_path = src_path / "notebooks"
    return notebook_path


def flatten(treelist, depth=0) -> dict:
    """Flatten a tree of activities into a flat list.

    Returns a dict with fields:
    ActivityID, ActivityName, activity,
    ParentId, ParentName, ParentLevel
    
    Parameters
    ----------
    treelist
        activity, or list or dict with activities
    depth
        depth level of top of hierarchy (default 0)
    """

    if isinstance(treelist,list):
        treelist = treelist
    elif isinstance(treelist,dict):
        treelist = [*treelist.values()]
    else:
        treelist = [treelist]
        
    activity = [x for x in treelist]
    ActivityID = [x.id for x in treelist]
    ActivityName = [x.name for x in treelist]
    ActivityClass = [type(x).__name__ for x in treelist]
    ParentId = [None,]*len(ActivityID)
    ParentName = ['',]*len(ActivityID)
    ParentLevel = [depth,]*len(ActivityID)
    
    for i, act in enumerate(treelist):
        if hasattr(act, "sub_processes"):
            d = flatten(act.sub_processes, depth+1)
            ActivityID += d['ActivityID']
            activity+=d['activity']
            ParentId +=[act.id]*len(d['activity'])
            ParentName +=[act.name]*len(d['ParentName'])
            ActivityClass +=d['ActivityClass']
            ActivityName +=d['ActivityName']
            ParentLevel +=d['ParentLevel']
           
    return {'ActivityID':ActivityID,
            'ActivityName':ActivityName,
            'ActivityClass':ActivityClass,
            'ParentId':ParentId,
            'ParentName':ParentName,
            'ParentLevel':ParentLevel,
            'activity':activity}

def export_concepts(concepts, namespace='', ofile=None,):
    """Save the concepts vities to a resolved csv file
    
    Concepts can be stored in 1 file (Sites and Vessels)
    or they can  be stored mixed together.

    Parameters
    ----------
    concepts
        concepts to be resolved and stored
    namespace
        str that will prepad the column names 'Name', 'ID', "Type".
        e.g. Vessel, Site or Concept
    ofile
        name of csv file to be exported
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list or dict of concepts
        * a manual id_map to resolve concept uuids to labels, e.g. {'uuid1':'vessel A'}
    """
    
    if isinstance(concepts,dict):
        concepts = [*concepts.values()] 
    
    df= {f'{namespace}Name':[x.name for x in concepts],
         f'{namespace}ID':[x.id for x in concepts],
         f'{namespace}Type':[type(x) for x in concepts]}
    
    df = pd.DataFrame(df)
    if ofile:
        df.to_csv(ofile, index=False)
    
    return df

def export_activities(activities, ofile=None, id_map=None):
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
    id_map
        by default uuids are not resolved. id_map solves this at request:
        * a list or dict of concepts
        * a manual id_map to resolve concept uuids to labels, e.g. {'uuid1':'vessel A'}
    """
    
    if isinstance(id_map, dict):
        id_map = [*id_map.values()]    
    if isinstance(id_map, list):
        id_map = {act.id: act.name for act in id_map} # needs to be recursive: flatten
    else:
        id_map = id_map if id_map else {}
    
    df = flatten(activities)
    
    df['ProcessorID']     = [x.processor.id   if hasattr(x,'processor')   else None for x in df['activity']]
    df['MoverID']         = [x.mover.id       if hasattr(x,'mover')       else None for x in df['activity']]
    df['OriginID']        = [x.origin.id      if hasattr(x,'origin')      else None for x in df['activity']]
    df['DestinationID']   = [x.destination.id if hasattr(x,'destination') else None for x in df['activity']]
    
    df['ProcessorName']   = [dict.get(id_map,x,'') for x in df['ProcessorID']]
    df['MoverName']       = [dict.get(id_map,x,'') for x in df['MoverID']]
    df['OriginName']      = [dict.get(id_map,x,'') for x in df['OriginID']]
    df['DestinationName'] = [dict.get(id_map,x,'') for x in df['DestinationID']]

    # manually set column order + exclude actual 'activity' object !
    
    keys  = ['ActivityID','ActivityName','ActivityClass',
             'ParentId','ParentName','ParentLevel',
             'OriginID','OriginName',
             'DestinationID','DestinationName',
             'ProcessorID','ProcessorName',
             'MoverID', 'MoverName'
            ]
    
    df = pd.DataFrame(df)
        
    if ofile:
        df.to_csv(ofile, columns = keys, index=False)
    
    return df

def export_ranges(all_act_flat, ofile = None, concept_name=None):
    """Save log of flattened activities list to a resolved start-stop list in a csv file

    This export of the logged time ranges can be used to plot Gannt 
    charts in for instance Qlik. Load the coupled export_activities() file
    to resolve the Activty properties and relations to (Sites and Vessels).


    Parameters
    ----------
    activities
        flattened list of activities to be resolved and stored
        use flatten()
    ofile
        name of csv file to be exported
    concept_name
        optional filter the flattened list for one 
        concept_name (Sites and Vessels)
    """

    if concept_name:
        logmask = (all_act_flat['ProcessorName']==concept_name) | \
                  (all_act_flat['MoverName']==concept_name)  | \
                  (all_act_flat['OriginName']==concept_name)  | \
                  (all_act_flat['DestinationName']==concept_name) 

        all_act_flat = all_act_flat[logmask]
    
    li = []
    for i, rowi in all_act_flat.iterrows():
        log = get_ranges_dataframe(rowi['activity'])
        log.rename(columns={'Activity':'ActivityID'}, inplace=True)
        li.append(log)
    ActivityRanges = pd.concat(li)
    
    ActivityRanges = ActivityRanges.merge(all_act_flat[['ActivityID', 'ActivityName', 'ActivityClass']], on='ActivityID', how='left')
    
    keys  = ['trip',
             'ActivityID','ActivityName','ActivityClass',
             'TimestampStart','TimestampStop','TimestampDt']
    if concept_name:
        ActivityRanges['ConceptName'] = concept_name
        keys+=['ConceptName']
        
    if ofile:
        ActivityRanges.to_csv(ofile, columns = keys, index=False)
    
    return ActivityRanges.sort_values(by=["TimestampStart"])

