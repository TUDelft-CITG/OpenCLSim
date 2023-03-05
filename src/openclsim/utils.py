import pathlib

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

    Returns a dict with fields: ActivityID,ActivityName,
    ParentId, ParentName, activity,level
    
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
    ActivityType = [type(x).__name__ for x in treelist]
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
            ActivityType +=d['ActivityType']
            ActivityName +=d['ActivityName']
            ParentLevel +=d['ParentLevel']
           
    return {'ActivityID':ActivityID,
            'ActivityName':ActivityName,
            'ActivityType':ActivityType,
            'ParentId':ParentId,
            'ParentName':ParentName,
            'ParentLevel':ParentLevel,
            'activity':activity}

