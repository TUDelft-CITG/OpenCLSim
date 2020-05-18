import functools
import io
import datetime

import pandas as pd
import numpy as np

# plotting libraries
import plotly
from plotly.offline import init_notebook_mode, iplot
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from matplotlib.collections import LineCollection

# spatial libraries
import pyproj
import shapely.geometry
from simplekml import Kml, Style

import flask

import networkx as nx


def demo_plot():
    """example plot"""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    return fig


def fig2response(fig):
    """return a figure as a response"""
    stream = io.BytesIO()
    format = "png"
    fig.savefig(stream, format=format)
    mimetype = "image/png"
    # rewind the stream
    stream.seek(0)
    return flask.send_file(stream, mimetype=mimetype)


def vessel_planning(vessels, activities, colors, web=False, static=False):
    """create a plot of the planning of vessels"""

    def get_segments(series, activity, y_val):
        """extract 'start' and 'stop' of activities from log"""
        x = []
        y = []
        for i, v in series.iteritems():
            if v == activity + " start":
                start = i
            if v == activity + " stop":
                x.extend((start, start, i, i, i))
                y.extend((y_val, y_val, y_val, y_val, None))
        return x, y

    # organise logdata into 'dataframes'
    dataframes = []
    for vessel in vessels:
        df = pd.DataFrame(
            {"log_value": vessel.log["Value"], "log_string": vessel.log["Message"]},
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
            x, y = get_segments(df["log_string"], activity=activity, y_val=y_val)
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


def vessel_kml(
    env,
    vessels,
    fname="vessel_movements.kml",
    icon="http://maps.google.com/mapfiles/kml/shapes/sailing.png",
    size=1,
    scale=1,
    stepsize=120,
):
    """Create a kml visualisation of vessels. Env variable needs to contain
    epoch to enable conversion of simulation time to real time. Vessels need
    logs that contain geometries in lat, lon as a function of time."""

    # create a kml file containing the visualisation
    kml = Kml()
    fol = kml.newfolder(name="Vessels")

    shared_style = Style()
    shared_style.labelstyle.color = "ffffffff"  # White
    shared_style.labelstyle.scale = size
    shared_style.iconstyle.color = "ffff0000"  # Blue
    shared_style.iconstyle.scale = scale
    shared_style.iconstyle.icon.href = icon

    # each timestep will be represented as a single point
    for vessel in vessels:
        geom_x = []
        geom_y = []

        for geom in vessel.log["Geometry"]:
            geom_x.append(geom.x)
            geom_y.append(geom.y)

        vessel.log["Geometry - x"] = geom_x
        vessel.log["Geometry - y"] = geom_y

        time_stamp_min = min(vessel.log["Timestamp"]).timestamp()
        time_stamp_max = max(vessel.log["Timestamp"]).timestamp()

        steps = int(np.floor((time_stamp_max - time_stamp_min) / stepsize))
        timestamps_t = np.linspace(time_stamp_min, time_stamp_max, steps)

        times = []
        for t in vessel.log["Timestamp"]:
            times.append(t.timestamp())

        vessel.log["timestamps_t"] = timestamps_t
        vessel.log["timestamps_x"] = np.interp(
            timestamps_t, times, vessel.log["Geometry - x"]
        )
        vessel.log["timestamps_y"] = np.interp(
            timestamps_t, times, vessel.log["Geometry - y"]
        )

        for log_index, value in enumerate(vessel.log["timestamps_t"][:-1]):

            begin = datetime.datetime.fromtimestamp(
                vessel.log["timestamps_t"][log_index]
            )
            end = datetime.datetime.fromtimestamp(
                vessel.log["timestamps_t"][log_index + 1]
            )

            pnt = fol.newpoint(
                name=vessel.name,
                coords=[
                    (
                        vessel.log["timestamps_x"][log_index],
                        vessel.log["timestamps_y"][log_index],
                    )
                ],
            )
            pnt.timespan.begin = begin.isoformat()
            pnt.timespan.end = end.isoformat()
            pnt.style = shared_style

        # include last point as well
        begin = datetime.datetime.fromtimestamp(
            vessel.log["timestamps_t"][log_index + 1]
        )
        # end = datetime.datetime.fromtimestamp(vessel.log["timestamps_t"][log_index + 1])

        pnt = fol.newpoint(
            name=vessel.name,
            coords=[
                (
                    vessel.log["timestamps_x"][log_index + 1],
                    vessel.log["timestamps_y"][log_index + 1],
                )
            ],
        )
        pnt.timespan.begin = begin.isoformat()
        # pnt.timespan.end = end.isoformat()
        pnt.style = shared_style

    kml.save(fname)


def site_kml(
    env,
    sites,
    fname="site_development.kml",
    icon="http://maps.google.com/mapfiles/kml/shapes/square.png",
    size=1,
    scale=3,
    stepsize=120,
):
    """Create a kml visualisation of vessels. Env variable needs to contain
    epoch to enable conversion of simulation time to real time. Vessels need
    logs that contain geometries in lat, lon as a function of time."""

    # create a kml file containing the visualisation
    kml = Kml()
    fol = kml.newfolder(name="Sites")

    # each timestep will be represented as a single point
    for site in sites:
        for log_index, value in enumerate(site.log["Timestamp"][:-1]):
            style = Style()
            style.labelstyle.color = "ffffffff"  # White
            style.labelstyle.scale = 1
            style.iconstyle.color = "ff00ffff"  # Yellow
            style.iconstyle.scale = scale * (
                site.log["Value"][log_index] / site.container.get_capacity()
            )
            style.iconstyle.icon.href = icon

            begin = site.log["Timestamp"][log_index]
            end = site.log["Timestamp"][log_index + 1]

            pnt = fol.newpoint(
                name=site.name,
                coords=[
                    (
                        site.log["Geometry"][log_index].x,
                        site.log["Geometry"][log_index].y,
                    )
                ],
            )
            pnt.timespan.begin = begin.isoformat()
            pnt.timespan.end = end.isoformat()
            pnt.style = style

        # include last point as well
        style = Style()
        style.labelstyle.color = "ffffffff"  # White
        style.labelstyle.scale = 1
        style.iconstyle.color = "ff00ffff"  # Yellow
        style.iconstyle.scale = scale * (
            site.log["Value"][log_index + 1] / site.container.get_capacity()
        )
        style.iconstyle.icon.href = icon

        begin = site.log["Timestamp"][log_index + 1]
        # end = site.log["Timestamp"][log_index + 1]

        pnt = fol.newpoint(
            name=site.name,
            coords=[
                (
                    site.log["Geometry"][log_index + 1].x,
                    site.log["Geometry"][log_index + 1].y,
                )
            ],
        )
        pnt.timespan.begin = begin.isoformat()
        # pnt.timespan.end = end.isoformat()
        pnt.style = style

    kml.save(fname)


def graph_kml(
    env,
    fname="graph.kml",
    icon="http://maps.google.com/mapfiles/kml/shapes/donut.png",
    size=0.5,
    scale=0.5,
    width=5,
):
    """Create a kml visualisation of graph. Env variable needs to contain
    graph."""

    # create a kml file containing the visualisation
    kml = Kml()
    fol = kml.newfolder(name="Vessels")

    shared_style = Style()
    shared_style.labelstyle.color = "ffffffff"  # White
    shared_style.labelstyle.scale = size
    shared_style.iconstyle.color = "ffffffff"  # White
    shared_style.iconstyle.scale = scale
    shared_style.iconstyle.icon.href = icon
    shared_style.linestyle.color = "ff0055ff"  # Red
    shared_style.linestyle.width = width

    nodes = list(env.FG.nodes)

    # each timestep will be represented as a single point
    for log_index, _ in enumerate(list(env.FG.nodes)[0 : -1 - 1]):

        pnt = fol.newpoint(
            name="",
            coords=[
                (
                    nx.get_node_attributes(env.FG, "Geometry")[nodes[log_index]].x,
                    nx.get_node_attributes(env.FG, "Geometry")[nodes[log_index]].y,
                )
            ],
        )
        pnt.style = shared_style

    edges = list(env.FG.edges)
    for log_index, _ in enumerate(list(env.FG.edges)[0 : -1 - 1]):

        lne = fol.newlinestring(
            name="",
            coords=[
                (
                    nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][0]].x,
                    nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][0]].y,
                ),
                (
                    nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][1]].x,
                    nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][1]].y,
                ),
            ],
        )
        lne.style = shared_style

    kml.save(fname)


def energy_use(vessels, testing=False, web=False):
    energy_use_loading = 0  # concumption between loading start and loading stop
    # concumption between sailing filled start and sailing filled stop
    energy_use_sailing_filled = 0
    # concumption between unloading  start and unloading  stop
    energy_use_unloading = 0
    # concumption between sailing empty start and sailing empty stop
    energy_use_sailing_empty = 0
    energy_use_waiting = 0  # concumption between waiting start and waiting stop

    def get_energy_use(vessel):
        energy_use_loading = 0  # concumption between loading start and loading stop
        # concumption between sailing filled start and sailing filled stop
        energy_use_sailing_filled = 0
        # concumption between unloading  start and unloading  stop
        energy_use_unloading = 0
        # concumption between sailing empty start and sailing empty stop
        energy_use_sailing_empty = 0
        energy_use_waiting = 0  # concumption between waiting start and waiting stop

        for i in range(len(vessel.log["Message"])):
            if vessel.log["Message"][i] == "Energy use loading":
                energy_use_loading += vessel.log["Value"][i]

            elif vessel.log["Message"][i] == "Energy use sailing filled":
                energy_use_sailing_filled += vessel.log["Value"][i]

            elif vessel.log["Message"][i] == "Energy use unloading":
                energy_use_unloading += vessel.log["Value"][i]

            elif vessel.log["Message"][i] == "Energy use sailing empty":
                energy_use_sailing_empty += vessel.log["Value"][i]

            elif vessel.log["Message"][i] == "Energy use waiting":
                energy_use_waiting += vessel.log["Value"][i]

        return (
            energy_use_loading,
            energy_use_sailing_filled,
            energy_use_unloading,
            energy_use_sailing_empty,
            energy_use_waiting,
        )

    try:
        for vessel in vessels:
            energy = get_energy_use(vessel)
            energy_use_loading += energy[0]
            energy_use_sailing_filled += energy[1]
            energy_use_unloading += energy[2]
            energy_use_sailing_empty += energy[3]
            energy_use_waiting += energy[4]

    except TypeError:
        energy = get_energy_use(vessels)
        energy_use_loading += energy[0]
        energy_use_sailing_filled += energy[1]
        energy_use_unloading += energy[2]
        energy_use_sailing_empty += energy[3]
        energy_use_waiting += energy[4]

    # For the total plot
    fig, ax1 = plt.subplots(figsize=[15, 10])

    # For the barchart
    height = [
        energy_use_loading,
        energy_use_unloading,
        energy_use_sailing_filled,
        energy_use_sailing_empty,
        energy_use_waiting,
    ]
    labels = ["Loading", "Unloading", "Sailing filled", "Sailing empty", "Waiting"]
    colors = [
        (55 / 255, 126 / 255, 184 / 255),
        (255 / 255, 150 / 255, 0 / 255),
        (98 / 255, 192 / 255, 122 / 255),
        (98 / 255, 141 / 255, 122 / 255),
        (255 / 255, 0 / 255, 0 / 255),
    ]

    positions = np.arange(len(labels))
    ax1.bar(positions, height, color=colors)

    # For the cumulative percentages
    total_use = sum(
        [
            energy_use_loading,
            energy_use_unloading,
            energy_use_sailing_filled,
            energy_use_sailing_empty,
            energy_use_waiting,
        ]
    )

    energy_use_unloading += energy_use_loading
    energy_use_sailing_filled += energy_use_unloading
    energy_use_sailing_empty += energy_use_sailing_filled
    energy_use_waiting += energy_use_sailing_empty
    y = [
        energy_use_loading,
        energy_use_unloading,
        energy_use_sailing_filled,
        energy_use_sailing_empty,
        energy_use_waiting,
    ]
    n = [
        energy_use_loading / total_use,
        energy_use_unloading / total_use,
        energy_use_sailing_filled / total_use,
        energy_use_sailing_empty / total_use,
        energy_use_waiting / total_use,
    ]

    ax1.plot(positions, y, "ko", markersize=10)
    ax1.plot(positions, y, "k")

    for i, txt in enumerate(n):
        x_txt = positions[i] + 0.1
        y_txt = y[i] * 0.95
        ax1.annotate("{:02.1f}%".format(txt * 100), (x_txt, y_txt), size=12)

    # Further markup
    ax1.set_ylabel("Energy useage in kWh", size=12)
    ax1.set_xticks(positions)
    ax1.set_xticklabels(labels, size=12)

    try:
        _ = len(vessels)
        ax1.set_title("Energy use - for all equipment", size=15)
    except:
        ax1.set_title("Energy use - {}".format(vessels.name), size=15)

    if testing == False:
        if web == False:
            plt.show()
        else:
            return fig


def activity_distribution(vessel, testing=False):
    activities = ["loading", "unloading", "sailing filled", "sailing empty", "waiting"]
    activities_times = [0, 0, 0, 0, 0]

    for i, activity in enumerate(activities):
        starts = []
        stops = []

        for j, message in enumerate(vessel.log["Message"]):
            if activity != "waiting":
                if message == activity + " start":
                    starts.append(vessel.log["Timestamp"][j])
                if message == activity + " stop":
                    stops.append(vessel.log["Timestamp"][j])
            else:
                if message[:7] == activity and message[-5:] == "start":
                    starts.append(vessel.log["Timestamp"][j])
                if message[:7] == activity and message[-4:] == "stop":
                    stops.append(vessel.log["Timestamp"][j])

        for j, _ in enumerate(starts):
            activities_times[i] += (stops[j] - starts[j]).total_seconds() / (3600 * 24)

    loading, unloading, sailing_full, sailing_empty, waiting = (
        activities_times[0],
        activities_times[1],
        activities_times[2],
        activities_times[3],
        activities_times[4],
    )

    # For the total plot
    fig, ax1 = plt.subplots(figsize=[15, 10])

    # For the barchart
    height = [loading, unloading, sailing_full, sailing_empty, waiting]
    labels = ["Loading", "Unloading", "Sailing full", "Sailing empty", "Waiting"]
    colors = [
        (55 / 255, 126 / 255, 184 / 255),
        (255 / 255, 150 / 255, 0 / 255),
        (98 / 255, 192 / 255, 122 / 255),
        (98 / 255, 141 / 255, 122 / 255),
        (255 / 255, 0 / 255, 0 / 255),
    ]

    positions = np.arange(len(labels))
    ax1.bar(positions, height, color=colors)

    # For the cumulative percentages
    total = sum([loading, unloading, sailing_full, sailing_empty, waiting])

    unloading += loading
    sailing_full += unloading
    sailing_empty += sailing_full
    waiting += sailing_empty
    y = [loading, unloading, sailing_full, sailing_empty, waiting]
    n = [
        loading / total,
        unloading / total,
        sailing_full / total,
        sailing_empty / total,
        waiting / total,
    ]

    ax1.plot(positions, y, "ko", markersize=10)
    ax1.plot(positions, y, "k")

    for i, txt in enumerate(n):
        x_txt = positions[i] + 0.1
        y_txt = y[i] * 0.95
        ax1.annotate("{:02.1f}%".format(txt * 100), (x_txt, y_txt), size=12)

    # Further markup
    ax1.set_ylabel("Total time spend on activities [Days]", size=12)
    ax1.set_xticks(positions)
    ax1.set_xticklabels(labels, size=12)
    ax1.set_title("Distribution of spend time - {}".format(vessel.name), size=15)

    if testing == False:
        plt.show()


def equipment_plot_json(vessels, web=False):

    # Set up the basic storage
    equipment_dict = {}
    activities = ["sailing empty", "loading", "sailing filled", "unloading"]

    y = 0
    ys = []
    names = []

    date_start = datetime.datetime(2100, 1, 1)
    date_end = datetime.datetime(1970, 1, 1)

    for vessel in vessels:
        equipment_dict[vessel.name] = {
            "sailing empty": [],
            "loading": [],
            "sailing filled": [],
            "unloading": [],
        }

        df = pd.DataFrame.from_dict(vessel.log)
        y += 0.5

        ys.append(y)
        names.append(vessel.name)

        for i, msg in enumerate(df["Message"]):
            date = datetime.datetime.strptime(
                str(df["Timestamp"][i]), "%Y-%m-%d %H:%M:%S"
            )

            if date < date_start:
                date_start = date
            if date > date_end:
                date_end = date

            date = date2num(date)

            for act in activities:
                if act + " start" == msg:
                    to_app = (date, y)
                    equipment_dict[vessel.name][act].append([to_app])

                elif act + " stop" == msg:
                    to_app = (date, y)
                    equipment_dict[vessel.name][act][-1].append(to_app)

    equipment_fig, equipment_ax = plt.subplots(figsize=[16, 8])

    sailing_empty = []
    sailing_full = []
    unloading = []
    loading = []

    for vessel in vessels:
        sailing_empty += equipment_dict[vessel.name]["sailing empty"]
        sailing_full += equipment_dict[vessel.name]["sailing filled"]
        unloading += equipment_dict[vessel.name]["unloading"]
        loading += equipment_dict[vessel.name]["loading"]

    act_1 = LineCollection(
        sailing_empty,
        label="Sailing empty",
        linewidths=10,
        color=(98 / 255, 141 / 255, 122 / 255),
    )
    act_2 = LineCollection(
        sailing_full,
        label="Sailing filled",
        linewidths=10,
        color=(98 / 255, 192 / 255, 122 / 255),
    )
    act_3 = LineCollection(
        unloading,
        label="Unloading",
        linewidths=10,
        color=(255 / 255, 150 / 255, 0 / 255),
    )
    act_4 = LineCollection(
        loading, label="Loading", linewidths=10, color=(55 / 255, 126 / 255, 184 / 255)
    )

    equipment_ax.add_collection(act_1)
    equipment_ax.add_collection(act_2)
    equipment_ax.add_collection(act_3)
    equipment_ax.add_collection(act_4)

    equipment_ax.set_ylim(0, y + 0.25)
    equipment_ax.set_yticks(ys)
    equipment_ax.set_yticklabels(names)

    equipment_ax.set_xlim(date2num(date_start) - 0.25, date2num(date_end) + 0.25)
    equipment_ax.set_xticks([date2num(date_start), date2num(date_end)])
    equipment_ax.set_xticklabels([date_start, date_end])

    equipment_ax.legend(loc="lower right")
    equipment_ax.set_title("Equipment planning")

    if web == False:
        plt.show()
    else:
        return equipment_fig


def energy_use_time(vessels, web=False):

    energy_fig, energy_ax = plt.subplots(figsize=[16, 8])

    y_max = 0

    date_start = datetime.datetime(2100, 1, 1)
    date_end = datetime.datetime(1970, 1, 1)

    for vessel in vessels:
        df = pd.DataFrame.from_dict(vessel.log)
        x = []
        y = []

        x.append(
            date2num(
                datetime.datetime.strptime(str(df["Timestamp"][0]), "%Y-%m-%d %H:%M:%S")
            )
        )
        y.append(0)

        for i, msg in enumerate(df["Message"]):
            date = datetime.datetime.strptime(
                str(df["Timestamp"][i]), "%Y-%m-%d %H:%M:%S"
            )

            if date < date_start:
                date_start = date
            if date > date_end:
                date_end = date

            date = date2num(date)

            if "Energy use" in msg:
                x.append(date)
                y.append(y[-1] + df["Value"][i] * 0.2 * 3.5 / 1000)

        energy_ax.plot(x, y, label=vessel.name)
        if max(y) > y_max:
            y_max = max(y)

    energy_ax.set_ylim(0, y_max * 1.05)

    energy_ax.set_xlim(date2num(date_start) - 0.25, date2num(date_end) + 0.25)
    energy_ax.set_xticks([date2num(date_start), date2num(date_end)])
    energy_ax.set_xticklabels([date_start, date_end])

    energy_ax.legend(loc="lower right")
    energy_ax.set_title("ton CO2 emission per vessel")

    if web == False:
        plt.show()
    else:
        return energy_fig


def styled(f, style="ggplot"):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        # execute in temporary styled context
        with plt.style.use(style):
            result = f(*args, **kwds)
        return result

    return wrapper


@styled
def plot_route(vessels):
    import matplotlib.pyplot as plt

    from cartopy import config
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap, BoundaryNorm

    fig = plt.figure(figsize=(10, 10))
    ax = plt.subplot(projection=ccrs.Mercator(), figure=fig)
    ax.coastlines(resolution="10m", color="black", linewidth=3)
    ax.gridlines(color="grey", zorder=3)
    ax.add_feature(
        cfeature.NaturalEarthFeature(
            "physical", "land", "10m", edgecolor="face", facecolor="palegoldenrod"
        )
    )

    for hopper in vessels:
        Hopper_route = hopper.log["Geometry"]
        x_loc = []
        y_loc = []
        for G in Hopper_route:
            x_loc.append(G.x)
            y_loc.append(G.y)
        x_loc = np.array(x_loc)
        y_loc = np.array(y_loc)

        TT = hopper.log["Timestamp"]
        Time = []

        for T in TT:
            TTT = T.timestamp()
            Time.append(TTT)

        Time = np.array(Time)
        Time = (Time - Time[0]) / 3600 / 24

        points = np.array([x_loc, y_loc]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        norm = plt.Normalize(Time.min(), Time.max())
        lc = LineCollection(
            segments, cmap="magma", norm=norm, transform=ccrs.PlateCarree()
        )

        lc.set_array(Time)
        line = ax.add_collection(lc)
        fig.colorbar(line, ax=ax, label="Time in days")

        ax.set_extent(
            [
                x_loc.min() * 0.99,
                x_loc.max() * 1.01,
                y_loc.min() * 0.999,
                y_loc.max() * 1.001,
            ]
        )

    return fig
