"""Get the log of the simulation objects in a pandas dataframe."""

import pandas as pd


def get_log_dataframe(simulation_object, activities=[]):
    """Get the log of the simulation objects in a pandas dataframe.
    
    Parameters
    ----------
    simulation_object
        object from which the log is returned as a dataframe sorted by "Timestamp"
    activities: list
        a list of activity objects that that is used to replace the unique 
        object id (uuid) with the human readable name.
    
    """

    id_map = {act.id: act.name for act in activities}

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
