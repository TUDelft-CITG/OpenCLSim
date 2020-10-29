"""Get the step chart of the container levels."""

import matplotlib.pyplot as plt

from .log_dataframe import get_log_dataframe


def get_step_chart(simulation_objects):
    """Get the step chart of the container levels."""

    fig = plt.figure()
    for obj in simulation_objects:
        df = get_log_dataframe(obj)
        container_list = obj.container.container_list
        for container in container_list:
            container = f" {container}" if container != "default" else ""
            plt.plot(
                list(df["Timestamp"]),
                list(df[f"container level{container}"]),
                label=f"{obj.name}{container}",
            )
    plt.legend()
    return fig
