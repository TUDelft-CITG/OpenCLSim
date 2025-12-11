"""Script that generates a vessel planning for a given simulation."""

import random

import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, iplot

from openclsim.model import get_subprocesses

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
    for index, row in df.iterrows():
        if "START" in row["activity_state"] and row["log_string"] == activity:
            start = index
        elif "STOP" in row["activity_state"] and row["log_string"] == activity:
            x.extend((start, start, index, index, index))
            y.extend((y_val, y_val, y_val, y_val, None))
    return x, y


def get_gantt_chart(
    concepts,
    activities=None,
    id_map=None,
    colors=None,
    web=False,
    static=False,
    y_scale="text",
):
    """Create a plotly GANTT chart of the planning of vessels.

    Parameters
    ----------
    concepts
        a list or dict of vessels, sites or activities for which to plot all
        activities, e.g.: [while_activity1, while_activity2] or
        {'w1':while_activity1, 'w2:while_activity2'}. Combinations of list
        and dicts need to be merged first into 1 overall list or dict, e.g.
        concepts = [from_site, to_site, *vessels.values()]
    activities
        a list or dict of additional activities to be plotted,
        if not yet in concepts
    id_map
        by default only the legend labels of activities in concepts are
        resolved. Activities associated with vessels and sites are not
        resolved. id_map resolves the legend labels using extra metadata:
        * a list or dict of vessels
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}

    """
    default_blockwidth = 10

    # unpack dict to list
    if type(concepts) is dict:
        concepts = [*concepts.values()]

    if type(activities) is dict:
        activities = [*activities.values()]

    if type(id_map) is dict:
        id_map = [*id_map.values()]

    if type(id_map) is list:
        id_map = {act.id: act.name for act in get_subprocesses(id_map)}
    else:
        id_map = id_map if id_map else {}
    act_map = {ves.id: ves.name for ves in concepts}

    if activities is None:
        activities = []
        for obj in concepts:
            activities.extend(set(obj.log["ActivityID"]))

    if colors is None:
        C = get_colors(len(activities))
        colors = {}
        for i in range(len(activities)):
            colors[i] = f"rgb({C[i][0]},{C[i][1]},{C[i][2]})"

    # organise logdata into 'dataframes'
    dataframes = []
    names = []
    for vessel in concepts:
        if len(vessel.log["Timestamp"]) > 0:
            df = get_log_dataframe(vessel, concepts).rename(
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
                line=dict(color=colors[i], width=default_blockwidth),
                connectgaps=False,
            )
        )

    timestamps = []
    logs = [o.log["Timestamp"] for o in concepts]
    for log in logs:
        timestamps.extend(log)

    return add_layout_gantt_chart(traces, min(timestamps), max(timestamps), static)


def add_layout_gantt_chart(traces, xmin, xmax, static):
    """
    Given the plotly data (traces), add the layout and return the
     resulting figure.

    Parameters
    ----------
    traces : list
        contains data/plotly objects for plotting in go.Figure().
    xmin : float
        min value for x-axis of plot
    xmax : float
        max value for x-axis of plot
    static : boolean
        If True, return data and layout in dictionairy.
        if False, a go.Figure is generated with iplot.

    """

    layout = go.Layout(
        title="GANTT Chart",
        hovermode="closest",
        legend={"x": 0, "y": -0.2, "orientation": "h"},
        xaxis={
            "title": {
                "text": "Time",
                "font": {
                    "family": "Courier New, monospace",
                    "size": 18,
                    "color": "#7f7f7f",
                },
            },
            "range": [xmin, xmax],
        },
        yaxis={
            "title": {
                "text": "Activities",
                "font": {
                    "family": "Courier New, monospace",
                    "size": 18,
                    "color": "#7f7f7f",
                },
            },
        },
    )

    if static is False:
        init_notebook_mode(connected=True)
        fig = go.Figure(data=traces, layout=layout)

        return iplot(fig, filename="news-source")
    else:
        return {"data": traces, "layout": layout}
