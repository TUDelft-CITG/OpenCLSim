"""Script that generates a vessel planning for a given simulation."""

import random

import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, iplot

from .log_dataframe import get_log_dataframe


def get_colors(n):
    """Get random colors for the activities."""
    ret = []
    r = int(random.random() * 256)
    g = int(random.random() * 256)
    b = int(random.random() * 256)
    step = 256 / n
    for i in range(n):
        r += step
        g += step
        b += step
        r = int(r) % 256
        g = int(g) % 256
        b = int(b) % 256
        ret.append((r, g, b))
    return ret


def get_segments(df, activity, y_val):
    """Extract 'start' and 'stop' of activities from log."""
    x = []
    y = []
    start = 0
    for i in range(len(df)):
        if "START" in df["activity_state"][i] and df["log_string"][i] == activity:
            start = df.index[i]
        elif "STOP" in df["activity_state"][i] and df["log_string"][i] == activity:
            x.extend((start, start, df.index[i], df.index[i], df.index[i]))
            y.extend((y_val, y_val, y_val, y_val, None))
    return x, y


def get_gantt_chart(
    vessels,
    activities=None,
    id_map=None,
    colors=None,
    web=False,
    static=False,
    y_scale="text",
):
    """Create a plot of the planning of vessels."""
    id_map = id_map if id_map else {}
    act_map = {ves.id: ves.name for ves in vessels}

    if activities is None:
        activities = []
        for obj in vessels:
            activities.extend(set(obj.log["ActivityID"]))

    if colors is None:
        C = get_colors(len(activities))
        colors = {}
        for i in range(len(activities)):
            colors[i] = f"rgb({C[i][0]},{C[i][1]},{C[i][2]})"

    # organise logdata into 'dataframes'
    dataframes = []
    names = []
    for vessel in vessels:
        if len(vessel.log["Timestamp"]) > 0:
            df = get_log_dataframe(vessel, vessels).rename(
                columns={
                    "Activity": "log_string",
                    "ActivityState": "activity_state",
                }
            )
            df = (
                df.drop(df[df.activity_state == "WAIT_START"].index)
                .drop(df[df.activity_state == "WAIT_STOP"].index)
                .set_index("Timestamp", drop=False)
            )

            dataframes.append(df)
            names.append(vessel.name)

    df = dataframes[0]
    # prepare traces for each of the activities
    traces = []
    for i, activity in enumerate(activities):
        activity = act_map.get(activity, activity)
        x_combined = []
        y_combined = []
        for k, df in enumerate(dataframes):
            y_val = -k if y_scale == "numbers" else names[k]
            x, y = get_segments(df, activity=activity, y_val=y_val)
            x_combined.extend(x)
            y_combined.extend(y)
        traces.append(
            go.Scatter(
                name=id_map.get(activity, activity),
                x=x_combined,
                y=y_combined,
                mode="lines",
                hoverinfo="y+name",
                line=dict(color=colors[i], width=10),
                connectgaps=False,
            )
        )

    timestamps = []
    logs = [o.log["Timestamp"] for o in vessels]
    for log in logs:
        timestamps.extend(log)

    layout = go.Layout(
        title="GANTT Chart",
        hovermode="closest",
        legend=dict(x=0, y=-0.2, orientation="h"),
        xaxis=dict(
            title="Time",
            titlefont=dict(family="Courier New, monospace", size=18, color="#7f7f7f"),
            range=[min(timestamps), max(timestamps)],
        ),
        yaxis=dict(
            title="Activities",
            titlefont=dict(family="Courier New, monospace", size=18, color="#7f7f7f"),
        ),
    )

    if static is False:
        init_notebook_mode(connected=True)
        fig = go.Figure(data=traces, layout=layout)

        return iplot(fig, filename="news-source")
    else:
        return {"data": traces, "layout": layout}
