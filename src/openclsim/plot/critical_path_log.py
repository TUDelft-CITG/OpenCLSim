"""
module for 'superlog' and creation of list of dependencies from such a superlog.

A superlog is a pd.DataFrame with certain column definition and contains activities -as logged -
of (all) source objects within simulation. The superlog has a column 'cp_activity_id' which differs from 'Activity',
because an activity id may recur at multiple times. An activity id in combination with a time window defines a
cp_activity_id (stands for critical path activity id).

"""
# external (pypi) dependencies
import datetime as dt
import logging

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, iplot

from openclsim.plot.graph_dependencies import DependencyGraph
from openclsim.plot.resource_capacity_dependencies import (
    get_resource_capacity_dependencies,
)
from openclsim.plot.start_wait_dependencies import (
    get_act_dependencies_start,
    get_wait_dependencies_cp,
)

# openclsim imports
from .graph import ActivityGraph
from .log_dataframe import (
    get_log_dataframe,
    get_log_dataframe_activity,
    get_subprocesses,
)

# a color list for plot function
DEF_COLORS = [
    "#ff0000",
    "#bfbfbf",
    "#305496",
    "#00b0f0",
    "#ffff00",
    "#00b050",
    "#990101",
    "#ED7D31",
    "#7030A0",
    "#1EB299",
    "#483700",
    "#CCECFF",
    "#c6e0b4",
    "#525252",
    "#f8cbad",
    "#bf95df",
    "darkred",
    "magenta",
    "cyan",
    "orange",
]


class CpLog:
    """
    class that creates as 'critical path' log from the combined logs of (all) simulation objects
    and activities within simulation.

    Class can be initialised with a list_objects and a list_activities.
    Please ensure these contain all simulation objects and (top node) activities from your simulation.

    Parameters
    ---------------
    list_objects : list
        list of (ALL) simulation objects (after simulation)
    list_activities : list
        list of (ALL) top-node activity objects (after simulation)
    """

    COLUMNS_LOG = [
        "Activity",
        "SimulationObject",
        "start_time",
        "state",
        "duration",
        "end_time",
        "cp_activity_id",
        "is_critical",
    ]

    def __init__(self, list_objects, list_activities):
        """dummy docstring"""
        # extract logs from all objects
        cp_log = self._make_critical_path_log(list_objects, list_activities)
        # init set all activities on being non-critical
        cp_log.loc[:, "is_critical"] = False
        self.cp_log = cp_log
        self.list_objects = list_objects
        self.list_activities = list_activities

        # attributes created with get_dependencies
        self.dependencies_act = None
        self.all_cp_dependencies = None

    def mark_critical_activities(self):
        """mark activites as critical"""
        # # mark critical activities
        my_graph = ActivityGraph(self.cp_log, self.all_cp_dependencies)
        list_actvities_critical = my_graph.mark_critical_activities()
        self.cp_log.loc[:, "is_critical"] = self.cp_log.loc[:, "cp_activity_id"].isin(
            list_actvities_critical
        )

    def get_dependencies(self, method="new"):
        """get dependencies"""
        if method == "new":
            # method that only creates dependencies when explicitly programmed
            # get dependencies from DependencyGraph
            my_graph = DependencyGraph(self.list_activities)
            self.dependencies_act = my_graph.getListDependencies()
            # also get dependencies from start events
            dependencies_start = get_act_dependencies_start(self.list_activities)
            cp_dependencies = get_dependencies_time(
                self.cp_log, self.dependencies_act + dependencies_start
            )

            # get cp dependencies based on resource utilisation vs capacity
            cp_depencies_res_limitation = get_resource_capacity_dependencies(
                self.cp_log, self.list_objects
            )

            # get cp dependencies 'WAIT'
            cp_dependencies_wait = get_wait_dependencies_cp(self.cp_log)
            self.all_cp_dependencies = list(
                set(
                    cp_dependencies + cp_depencies_res_limitation + cp_dependencies_wait
                )
            )
        else:
            # Deprecated method - using timestamps and (shared) simulation objects to assume dependencies
            self.all_cp_dependencies = self._get_dependencies_timebased()

        return self.all_cp_dependencies

    def _get_dependencies_timebased(self):
        """
        DEPRECATED - sets dependencies 'blind', i.e. purely based on timestamp and simulation object
        Find dependencies within all cp_activities based on timestamps.
        Allow dependencies with unequal cp_activities only when waiting.
        In this special case the code assume dependency when an activity stops
        and another activity starts at the exact same time

        Returns
        ------------
        dependencies : list
            list of tuplese e.g. [(A, C), (B, C), (C, F)]  when C depends on A and B and F on C
        """
        list_dependencies = []
        # loop over each unique cp_activity
        for cp_act in self.cp_log.loc[:, "cp_activity_id"].unique():
            # and find cp_activities that END when this one STARTS
            bool_this_activity = self.cp_log.loc[:, "cp_activity_id"] == cp_act
            bool_end_when_start = (
                self.cp_log.loc[:, "end_time"]
                == self.cp_log.loc[bool_this_activity, "start_time"].iloc[0]
            )
            bool_shared_source = self.cp_log.loc[:, "SimulationObject"].isin(
                list(self.cp_log.loc[bool_this_activity, "SimulationObject"])
            )
            # so standard dependencies requires identical time and (at least 1) shared Source Object
            bool_dependencies = (
                bool_shared_source & bool_end_when_start & ~bool_this_activity
            )
            if sum(bool_dependencies) > 0:
                dependencies = self.cp_log.loc[bool_dependencies, :]
                if "WAITING" in dependencies.loc[:, "state"].tolist():
                    # this activity depends on waiting meaning
                    # current activity might have been waiting on activity of other source object!
                    # we ASSUME that every activity of every source object with identical end time of this WAITING is a
                    # dependency for current activity
                    dependencies = self.cp_log.loc[
                        bool_end_when_start & ~bool_this_activity, :
                    ]
                # get all unique activities on which current cp_act depends
                activities_depending = dependencies.loc[:, "cp_activity_id"].unique()
                for act_dep in activities_depending:
                    list_dependencies.append((act_dep, cp_act))

        return list_dependencies

    def make_gantt_mpl(self, incl_legend=True):
        """
        Create a matplotlib gantt plot of the superlog. For testing purposes

        Returns
        ----------
        fig : plt.Figure
            matplotlibs pyplot figure handle/object
        ax : plt.Axes
            matplotlibs axes handle/object
        """
        df_cp_log = self.cp_log.copy(deep=True)
        if "is_critical" in list(self.cp_log.columns):
            print("Including critical path in plot (red line)")

        # replace 'Activiteit' simulation object with WAITING activity if applicable
        bool_rename = (df_cp_log.loc[:, "SimulationObject"] == "Activity") & (
            df_cp_log.loc[:, "state"] == "WAITING"
        )
        df_cp_log.loc[bool_rename, "SimulationObject"] = df_cp_log.loc[
            :, "state"
        ].astype(str) + df_cp_log.loc[:, "Activity"].astype(str)

        fig, ax = plt.subplots(1, 1)
        color_count = 0
        for idx_object, sim_object in enumerate(
            df_cp_log.loc[:, "SimulationObject"].unique()
        ):
            bool_selection = df_cp_log.loc[:, "SimulationObject"] == sim_object
            for idx, activity in enumerate(
                df_cp_log.loc[bool_selection, "Activity"].unique()
            ):
                # maybe combine activity with state?
                color = DEF_COLORS[color_count % len(DEF_COLORS)]
                color_count += 1
                bool_selection_activity = (
                    df_cp_log.loc[:, "Activity"] == activity
                ) & bool_selection
                ax.barh(
                    sim_object,
                    df_cp_log.loc[bool_selection_activity, "duration"],
                    left=df_cp_log.loc[bool_selection_activity, "start_time"],
                    color=color,
                    label=activity,
                )
                if "is_critical" in list(self.cp_log.columns):
                    bool_plot_critical = bool_selection_activity & (
                        df_cp_log.loc[:, "is_critical"]
                    )
                    if sum(bool_plot_critical) > 0:
                        idx_activity = list(
                            bool_plot_critical.index[bool_plot_critical]
                        )
                        for crit_act in idx_activity:
                            ax.plot(
                                [
                                    df_cp_log.loc[crit_act, "start_time"],
                                    df_cp_log.loc[crit_act, "end_time"],
                                ],
                                [idx_object, idx_object],
                                "-r",
                            )

        ax.set_title("WIP version gantt graph")
        if incl_legend:
            # legend may be a bit heavy so option to exlcude
            ax.legend(
                bbox_to_anchor=(1.04, 1),
                loc="upper left",
                borderaxespad=2,
                ncol=2,
                prop={"size": 10},
            )
            fig.subplots_adjust(right=0.6)  # space for legend on right

        return fig, ax

    def make_gantt_plotly(self, static=False):
        """
        Create a plotly GANTT chart of the superlog
        """
        df_cp_log = self.cp_log.copy(deep=True)
        # replace 'Activiteit' simulation object with WAITING activity if applicable
        bool_rename = (df_cp_log.loc[:, "SimulationObject"] == "Activity") & (
            df_cp_log.loc[:, "state"] == "WAITING"
        )
        df_cp_log.loc[bool_rename, "SimulationObject"] = "WAIT"
        traces = []
        color_count = 0
        # loop over unique combinations of source object and Activity
        for source_object in df_cp_log.loc[:, "SimulationObject"].unique():
            bool_selection = df_cp_log.loc[:, "SimulationObject"] == source_object
            for idx, activity in enumerate(
                df_cp_log.loc[bool_selection, "Activity"].unique()
            ):
                # plot all activities of this object
                color = DEF_COLORS[color_count % len(DEF_COLORS)]
                color_count += 1
                bool_selection_activity = (
                    df_cp_log.loc[:, "Activity"] == activity
                ) & bool_selection
                start_times = df_cp_log.loc[
                    bool_selection_activity, "start_time"
                ].tolist()
                end_times = df_cp_log.loc[bool_selection_activity, "end_time"].tolist()
                x_list = [[s, e, e] for s, e in zip(start_times, end_times)]
                x = [item for sublist in x_list for item in sublist]
                y = [source_object, source_object, None] * len(x)
                traces.append(
                    go.Scatter(
                        name=activity,
                        x=x,
                        y=y,
                        mode="lines",
                        hoverinfo="y+name",
                        line=dict(color=color, width=10),
                        connectgaps=False,
                    )
                )

        # add critical path based on 'names'
        if "is_critical" in list(df_cp_log.columns):
            x_critical = df_cp_log.loc[
                df_cp_log.loc[:, "is_critical"], "start_time"
            ].tolist()
            x_critical_end = df_cp_log.loc[
                df_cp_log.loc[:, "is_critical"], "end_time"
            ].tolist()
            ylist = df_cp_log.loc[
                df_cp_log.loc[:, "is_critical"], "SimulationObject"
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
                    line=dict(color="red", width=3),
                    connectgaps=False,
                )
            )

        layout = go.Layout(
            title="GANTT Chart",
            hovermode="closest",
            legend=dict(x=0, y=-0.2, orientation="h"),
            xaxis=dict(
                title="Time",
                titlefont=dict(
                    family="Courier New, monospace", size=18, color="#7f7f7f"
                ),
                range=[
                    min(df_cp_log.loc[:, "start_time"]),
                    max(df_cp_log.loc[:, "end_time"]),
                ],
            ),
            yaxis=dict(
                title="Activities",
                titlefont=dict(
                    family="Courier New, monospace", size=18, color="#7f7f7f"
                ),
            ),
        )

        if static is False:
            init_notebook_mode(connected=True)
            fig = go.Figure(data=traces, layout=layout)

            return iplot(fig, filename="news-source")
        else:
            return {"data": traces, "layout": layout}

    def _make_critical_path_log(self, list_objects, list_activities):
        """make one single log containing all activities and timestamp"""
        log_sim_objects = combine_logs(list_objects, list_activities)
        log_act = combine_logs_activities(list_activities)

        # combine these two, but first check which to ignore
        bool_keep = []
        for idx, row in log_act.iterrows():
            bool_within_sim_log = (
                (row.loc["ActivityID"] == log_sim_objects.loc[:, "ActivityID"])
                & (row.loc["Timestamp"] == log_sim_objects.loc[:, "Timestamp"])
                & (row.loc["ActivityState"] == log_sim_objects.loc[:, "ActivityState"])
            )
            if sum(bool_within_sim_log) == 0:
                # no hit, add
                bool_keep.append(idx)

        log_all = (
            pd.concat([log_sim_objects, log_act.loc[bool_keep, :]])
            .sort_values("Timestamp")
            .reset_index(drop=True)
        )

        # reshape into set of activities with start, duration and end
        log_cp = reshape_log(log_all)
        # add unique identifier for activities (may be shared by multiple objects)
        log_cp = add_unique_activity(log_cp)

        return log_cp


def get_dependencies_time(df_log_cp, dependencies_act):
    """get dependencies of 'critical path activities',
    i.e. activities with specific ID, start time and end time

    Loop through the dependencies as set by the user and if the times match it is DEFINITELY a dependency

    Parameters
    -----------------
    df_log_cp : pd.DataFrame
        log of all activities
    dependencies_act : list
        list of tuples of all (activity ID) dependencies
    """
    list_cp_dependencies = []

    for dep in dependencies_act:
        # B depends on A
        A, B = dep
        # find every A with a directly following B
        all_a = df_log_cp.loc[df_log_cp.loc[:, "ActivityID"] == A, :]
        for idx, row in all_a.iterrows():
            all_time_diffs = df_log_cp.loc[:, "start_time"] - row.loc["end_time"]
            bool_eligible_b = (df_log_cp.loc[:, "ActivityID"] == B) & (
                abs(all_time_diffs) < dt.timedelta(seconds=0.01)
            )
            cp_activities_b = list(
                set(df_log_cp.loc[bool_eligible_b, "cp_activity_id"])
            )
            if len(cp_activities_b) == 1:
                list_cp_dependencies.append(
                    (row.loc["cp_activity_id"], cp_activities_b[0])
                )
            else:
                logging.info(
                    f"No dependency found based on {row.loc['cp_activity_id']}"
                )
    # make unique - some duplicates are possible due to doubling of simulation objects
    list_cp_dependencies = list(set(list_cp_dependencies))

    return list_cp_dependencies


def reshape_log(df_log):
    """
    function to reshape df_log to activity with start and
    end times in 1 row (rather than row starts and rows stop)

    Parameters
    ------------
    df_log : pd.DataFrame()
        format like return from combine_logs() or plot.get_log_dataframe() function defs

    Returns
    ---------
    df_new : pd.DataFrame()
        like input but start and endtime on single row
    """
    df_log = df_log.sort_values(
        by=["Timestamp", "ActivityState"]
    )  # keep df chronological!!
    df_log = df_log.reset_index()
    to_handle = list(range(0, len(df_log)))
    df_new = pd.DataFrame()
    safety_valve = 0
    while len(to_handle) > 0 and safety_valve < len(df_log):
        safety_valve += 1
        idx_start = to_handle[0]
        row_current = df_log.loc[idx_start, :]
        if row_current.loc["ActivityState"] not in ["START", "WAIT_START"]:
            raise ValueError(
                f"Unexpected starting state {row_current.loc['ActivityState']} "
                f"for idx {idx_start}, so skipping this"
            )

        bool_candidates = (
            (df_log.loc[:, "ActivityID"] == row_current.loc["ActivityID"])
            & (df_log.loc[:, "SimulationObject"] == row_current.loc["SimulationObject"])
            & (df_log.loc[:, "ActivityState"].isin(["STOP", "WAIT_STOP"]))
        )
        idx_candidates = list(bool_candidates.index[bool_candidates])
        idx_end = [
            idx_end
            for idx_end in idx_candidates
            if idx_end > idx_start and idx_end in to_handle
        ][0]
        # now remove idx start and end from handle
        to_handle.remove(idx_start)
        to_handle.remove(idx_end)
        # and place in new dataframe
        df_new = pd.concat(
            [
                df_new,
                pd.DataFrame(
                    {
                        "Activity": row_current.loc["Activity"],
                        "ActivityID": row_current.loc["ActivityID"],
                        "SimulationObject": row_current.loc["SimulationObject"],
                        "start_time": row_current.loc["Timestamp"],
                        "state": "WAITING"
                        if "WAIT" in row_current.loc["ActivityState"]
                        else "ACTIVE",
                        "duration": df_log.loc[idx_end, "Timestamp"]
                        - row_current.loc["Timestamp"],
                        "end_time": df_log.loc[idx_end, "Timestamp"],
                    },
                    index=[0],
                ),
            ],
            ignore_index=True,
            sort=False,
        )

    # ASSUME that activities with duration zero can be discarded
    if isinstance(df_new.loc[:, "duration"][0], dt.timedelta):
        df_new = df_new.loc[df_new.loc[:, "duration"] > dt.timedelta(seconds=0), :]
    else:
        df_new = df_new.loc[df_new.loc[:, "duration"] > 0, :]

    assert len(to_handle) == 0, f"These have not been handled {to_handle}"
    df_new = df_new.sort_values(by=["start_time", "SimulationObject"])
    df_new = df_new.reset_index(drop=True)

    return df_new


def add_unique_activity(df_new):
    """
    Add unique identifier to each activity id and time combination
    for critical path note that a combination of activity (id) and time start and end is an unique activity,
    so thus we add this as cp_activity_id to the df

    Parameters
    -----------
    df_new : pd.DataFrame()
        like return from reshape_superlog()

    Returns
    ----------
    df_new : pd.DataFrame()
        has proper columns for input/init SuperLog
    """
    unique_combis = (
        df_new.groupby(["Activity", "start_time", "end_time"])
        .size()
        .reset_index()
        .rename(columns={0: "count"})
    )
    # now add unique ID to df_new
    for idx, row in unique_combis.iterrows():
        bool_match = (
            (df_new.loc[:, "Activity"] == row.loc["Activity"])
            & (df_new.loc[:, "start_time"] == row.loc["start_time"])
            & (df_new.loc[:, "end_time"] == row.loc["end_time"])
        )
        df_new.loc[bool_match, "cp_activity_id"] = f"cp_activity_{idx + 1}"

    return df_new


def combine_logs(objects, list_activities):
    """
    Combines the logs of given objects into a single dataframe.

    Parameters
    ------------
    objects : list
        a list of vessels, sites for which to plot all activities. These need to have had logging!
    list_activities : list
         a list of top-activities of which also all sub-activities will be resolved, e.g.: [while_activity]
    """
    # check unique names
    names = [obj.name for obj in objects]
    assert len(names) == len(set(names)), "Names of your objects must be unique!"

    # concat
    log_all = pd.DataFrame()
    for obj in objects:
        log = get_log_dataframe(obj)
        log["SimulationObject"] = obj.name
        log_all = pd.concat([log_all, log])
    # now drop some columns not directly needed
    log_all = log_all.loc[
        :, ["Activity", "Timestamp", "ActivityState", "SimulationObject"]
    ]
    # keep ID and add name for us humans
    log_all.loc[:, "ActivityID"] = log_all.loc[:, "Activity"]
    # get mapping
    list_all_activities = get_subprocesses(list_activities)
    id_map = {act.id: act.name for act in list_all_activities}
    log_all.loc[:, "Activity"] = log_all.loc[:, "Activity"].replace(id_map)

    return log_all.sort_values("Timestamp").reset_index(drop=True)


def combine_logs_activities(activities):
    """
    Combines the logs of given activities into a single dataframe.

    Parameters
    ------------
    activities : list
        a list of activities (after simulation). These need to have had logging!
    """
    # check unique names
    names = [act.name for act in activities]
    assert len(names) == len(set(names)), "Names of your objects must be unique!"

    # concat
    log_all = pd.DataFrame()
    for act in activities:
        log = get_log_dataframe_activity(act)
        log["SimulationObject"] = "Activity"
        log_all = pd.concat([log_all, log])

    return log_all.sort_values("Timestamp").reset_index(drop=True)
