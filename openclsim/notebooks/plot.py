import datetime
import pandas as pd
from plotly.offline import init_notebook_mode, iplot
import plotly.graph_objs as go


def vessel_planning(vessels, activities, colors, web=False, static=False):
    """create a plot of the planning of vessels"""

    def get_segments(df, activity, y_val):
        """extract 'start' and 'stop' of activities from log"""
        x = []
        y = []
        for i in range(len(df)):
            if df["activity_state"][i] == "START" and df["log_string"][i] == activity:
                start = df.index[i]
            if df["activity_state"][i] == "STOP" and df["log_string"][i] == activity:
                x.extend((start, start, df.index[i], df.index[i], df.index[i]))
                y.extend((y_val, y_val, y_val, y_val, None))
        return x, y

    # organise logdata into 'dataframes'
    dataframes = []
    for vessel in vessels:
        df = pd.DataFrame(
            {
                "log_value": vessel.log["Value"],
                "log_string": vessel.log["Message"],
                "activity_state": vessel.log["ActivityState"],
            },
            vessel.log["Timestamp"],
        )
        dataframes.append(df)
    df = dataframes[0]

    # prepare traces for each of the activities
    traces = []
    for i, activity in enumerate(activities):
        x_combined = []
        y_combined = []
        for k, df in enumerate(dataframes):
            y_val = vessels[k].name
            x, y = get_segments(df, activity=activity, y_val=y_val)
            x_combined.extend(x)
            y_combined.extend(y)
        traces.append(
            go.Scatter(
                name=activity,
                x=x_combined,
                y=y_combined,
                mode="lines",
                hoverinfo="y+name",
                line=dict(color=colors[i], width=10),
                connectgaps=False,
            )
        )

    # prepare layout of figure
    layout = go.Layout(
        title="Vessel planning",
        hovermode="closest",
        legend=dict(x=0, y=-0.2, orientation="h"),
        xaxis=dict(
            title="Time",
            titlefont=dict(family="Courier New, monospace", size=18, color="#7f7f7f"),
            range=[
                vessel.log["Timestamp"][0],
                vessel.log["Timestamp"][-1] + datetime.timedelta(seconds=4 * 3600),
            ],
        ),
        yaxis=dict(
            title="Vessels",
            titlefont=dict(family="Courier New, monospace", size=18, color="#7f7f7f"),
        ),
    )

    if static == False:
        # plot figure
        init_notebook_mode(connected=True)
        fig = go.Figure(data=traces, layout=layout)

        return iplot(fig, filename="news-source")
    else:
        fig = go.Figure(data=traces, layout=layout)
        return fig
