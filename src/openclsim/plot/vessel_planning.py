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
    for i in range(len(df)):
        if "START" in df["activity_state"][i] and df["log_string"][i] == activity:
            start = df.index[i]
        elif "STOP" in df["activity_state"][i] and df["log_string"][i] == activity:
            x.extend((start, start, df.index[i], df.index[i], df.index[i]))
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
    critical_path=None
):
    """Create a plotly GANTT chart of the planning of vessels.

    Parameters
    ----------
    concepts
        a list of vessels, sites or activities for which to plot all activities
    activities
        additional activities to be plotted, if not yet in concepts
    id_map
        by default only activity in concepts are resolved. Activities
        associated with vessels and sites are not resolved. id_map solves this:
        * a list of top-activities of which also all sub-activities
          will be resolved, e.g.: [while_activity]
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}
    """
    default_blockwidth = 10

    if type(id_map) == list:
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

    # extract the tracts for the cp to be plotted in the background
    traces = []
    if critical_path is not None:
        x_critical = critical_path.loc[
            critical_path.loc[:, "is_critical"], "start_time"
        ].tolist()

        x_critical_end = critical_path.loc[
            critical_path.loc[:, "is_critical"], "end_time"
        ].tolist()

        ylist = critical_path.loc[
            critical_path.loc[:, "is_critical"], "SimulationObject"
        ].tolist()

        x_nest = [[x1, x2, x2] for (x1, x2) in zip(x_critical, x_critical_end)]
        y_nest = [[y, y, None] for y in ylist]
        traces.append(
            go.Scatter(
                name="critical_path",
                x=[item for sublist in x_nest for item in sublist],
                y=[item for sublist in y_nest for item in sublist],
                mode="lines",
                hoverinfo="name",
                line=dict(color="red", width=default_blockwidth+4),
                connectgaps=False,
            )
        )

    df = dataframes[0]
    # prepare traces for each of the activities
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

    layout = go.Layout(
        title="GANTT Chart",
        hovermode="closest",
        legend=dict(x=0, y=-0.2, orientation="h"),
        xaxis=dict(
            title="Time",
            titlefont=dict(family="Courier New, monospace",
                           size=18, color="#7f7f7f"),
            range=[min(timestamps), max(timestamps)],
        ),
        yaxis=dict(
            title="Activities",
            titlefont=dict(family="Courier New, monospace",
                           size=18, color="#7f7f7f"),
        ),
    )

    if static is False:
        init_notebook_mode(connected=True)
        fig = go.Figure(data=traces, layout=layout)

        return iplot(fig, filename="news-source")
    else:
        return {"data": traces, "layout": layout}
