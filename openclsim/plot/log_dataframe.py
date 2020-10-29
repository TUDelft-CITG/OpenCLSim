"""Get the log of the simulation objects in a pandas dataframe."""

import pandas as pd


def get_log_dataframe(simulation_object, activities=[]):
    """Get the log of the simulation objects in a pandas dataframe."""

    id_map = {act.id: act.name for act in activities}
    return (
        pd.concat(
            [
                pd.DataFrame(simulation_object.log)[
                    ["Timestamp", "ActivityID", "ActivityState"]
                ],
                pd.DataFrame(simulation_object.log["ObjectState"]),
            ],
            axis=1,
        )
        .replace(id_map)
        .rename(columns={"ActivityID": "Activity"})
    )
