"""Get the step chart of the container levels."""

import matplotlib.pyplot as plt

from .log_dataframe import get_log_dataframe


def get_step_chart(simulation_objects, container_map=None):
    """Get the step chart of the container levels.

    Parameters
    ----------
    simulation_objects
        all vessels and sites for which the property "container level"
        will be plotted.
    container_map
        relabel container names, default {"default":""}
    """
    # default argument
    if container_map is None:
        container_map = {"default": ""}

    fig = plt.figure(figsize=(14, 7))
    for obj in simulation_objects:
        df = get_log_dataframe(obj)
        container_list = obj.container.container_list
        for container in container_list:
            if hasattr(df, "container level"):
                if isinstance(list(df["container level"])[0], dict) is False:
                    y = list(df["container level"])
                else:
                    y = [y[container] for y in list(df["container level"])]
                plt.plot(
                    list(df["Timestamp"]),
                    y,
                    label=f"{obj.name} {container_map.get(container,container)}",
                )
    plt.legend()
    return fig
