"""
module for 'superlog' and creation of list of dependencies from such a superlog.

A superlog is a pd.DataFrame with certain column definition and contains activities -as logged -
of (all) source objects within simulation. The superlog has a column 'cp_activity_id' which differs from 'Activity',
because an activity id may recur at multiple times. An activity id in combination with a time window defines a
cp_activity_id (stands for critical path activity id).

"""
# external (pypi) dependencies
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, iplot

# openclsim imports
import openclsim.plot as plot

# a color list for plot function
DEF_COLORS = ["#ff0000", "#bfbfbf", "#305496", "#00b0f0", "#ffff00", "#00b050", "#990101", "#ED7D31", "#7030A0",
              "#1EB299", "#483700", "#CCECFF", "#c6e0b4", "#525252", "#f8cbad", "#bf95df", "darkred", "magenta",
              "cyan", "orange"]


class SuperLog:
    """
    class that can get dependencies from the combined logs of (all) source objects with log within simulation.
    Also has a gannt plotter.

    Class can be initialised with an existing pd.DataFrame superlog or with the objects from simulation (class method)

    Parameters
    ---------------
    df_super_log : pd.DataFrame
        needs columns COLUMNS_SUPERLOG
    """
    COLUMNS_SUPERLOG = ['Activity', 'SourceObject', 'start_time', 'state', 'duration', 'end_time', 'cp_activity_id']

    def __init__(self, df_super_log):
        """ dummy docstring """
        assert set(self.COLUMNS_SUPERLOG).issubset(set(df_super_log.columns)), "df_super_log input is missing columns"

        # init
        # pd.Dataframe with columns as defince and optionally column 'is_critical' (and others)
        self.df_super_log = df_super_log
        # list of tuples e.g. [(A, C), (B, C), (C, F)]  when C depends on A and B and F on C
        self.dependencies = self._get_dependencies()

    def _get_dependencies(self):
        """
        set dependencies (list of tuples with cp_activity_id vales).
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
        for cp_act in self.df_super_log.loc[:, 'cp_activity_id'].unique():
            # and find cp_activities that END when this one STARTS
            bool_this_activity = self.df_super_log.loc[:, 'cp_activity_id'] == cp_act
            bool_end_when_start = self.df_super_log.loc[:, 'end_time'] == \
                                  self.df_super_log.loc[bool_this_activity, 'start_time'].iloc[0]
            bool_shared_source = self.df_super_log.loc[:, 'SourceObject'].isin(
                list(self.df_super_log.loc[bool_this_activity, 'SourceObject']))
            # so standard dependencies requires identical time and (at least 1) shared Source Object
            bool_dependencies = bool_shared_source & bool_end_when_start & ~bool_this_activity
            if sum(bool_dependencies) > 0:
                dependencies = self.df_super_log.loc[bool_dependencies, :]
                if "WAITING" in dependencies.loc[:, "state"].tolist():
                    # this activity depends on waiting meaning
                    # current activity might have been waiting on activity of other source object!
                    # we ASSUME that every activity of every source object with identical end time of this WAITING is a
                    # dependency for current activity
                    dependencies = self.df_super_log.loc[bool_end_when_start & ~bool_this_activity, :]
                # get all unique activities on which current cp_act depends
                activities_depending = dependencies.loc[:, 'cp_activity_id'].unique()
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
        if "is_critical" in list(self.df_super_log.columns):
            print("Including critical path in plot (black asterix)")

        fig, ax = plt.subplots(1, 1)
        color_count = 0
        for idx_object, sim_object in enumerate(self.df_super_log.loc[:, "SourceObject"].unique()):
            bool_selection = self.df_super_log.loc[:, "SourceObject"] == sim_object
            for idx, activity in enumerate(self.df_super_log.loc[bool_selection, "Activity"].unique()):
                # maybe combine activity with state?
                color = DEF_COLORS[color_count % len(DEF_COLORS)]
                color_count += 1
                bool_selection_activity = (self.df_super_log.loc[:, "Activity"] == activity) & bool_selection
                ax.barh(sim_object,  self.df_super_log.loc[bool_selection_activity, "duration"],
                        left=self.df_super_log.loc[bool_selection_activity, "start_time"], color=color, label=activity)
                if "is_critical" in list(self.df_super_log.columns):
                    bool_plot_critical = bool_selection_activity & (self.df_super_log.loc[:, "is_critical"])
                    if sum(bool_plot_critical) > 0:
                        idx_activity = list(bool_plot_critical.index[bool_plot_critical])
                        for crit_act in idx_activity:
                            ax.plot(self.df_super_log.loc[crit_act, "start_time"], idx_object, '*k')

        ax.set_title("WIP version gantt graph")
        if incl_legend:
            # legend may be a bit heavy so option to exlcude
            ax.legend(bbox_to_anchor=(1.04, 1), loc='upper left', borderaxespad=2, ncol=2, prop={'size': 10})
            fig.subplots_adjust(right=0.6)  # space for legend on right

        return fig, ax

    def make_gantt_plotly(self, static=False):
        """
        Create a plotly GANTT chart of the superlog
        """
        traces = []
        color_count = 0
        # loop over unique combinations of source object and Activity
        for source_object in self.df_super_log.loc[:, "SourceObject"].unique():
            bool_selection = self.df_super_log.loc[:, "SourceObject"] == source_object
            for idx, activity in enumerate(self.df_super_log.loc[bool_selection, "Activity"].unique()):
                # plot all activities of this object
                color = DEF_COLORS[color_count % len(DEF_COLORS)]
                color_count += 1
                bool_selection_activity = (self.df_super_log.loc[:, "Activity"] == activity) & bool_selection
                start_times = self.df_super_log.loc[bool_selection_activity, "start_time"].tolist()
                end_times = self.df_super_log.loc[bool_selection_activity, "end_time"].tolist()
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
                        connectgaps=False))

        # add critical path based on 'names'
        if "is_critical" in list(self.df_super_log.columns):
            x_critical = self.df_super_log.loc[self.df_super_log.loc[:, "is_critical"], "start_time"].tolist()
            y = self.df_super_log.loc[self.df_super_log.loc[:, "is_critical"], "SourceObject"].tolist()
            traces.append(go.Scatter(name="critical_path",
                                     x=x_critical,
                                     y=y,
                                     mode="markers",
                                     hoverinfo="name",
                                     line=dict(color='Black', width=5),
                                     connectgaps=False))
            print("DONE")

        layout = go.Layout(
            title="GANTT Chart",
            hovermode="closest",
            legend=dict(x=0, y=-0.2, orientation="h"),
            xaxis=dict(
                title="Time",
                titlefont=dict(family="Courier New, monospace", size=18, color="#7f7f7f"),
                range=[min(self.df_super_log.loc[:, "start_time"]), max(self.df_super_log.loc[:, "end_time"])],
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

    @classmethod
    def from_objects(cls, objects, id_map=None):
        """ get logs form objects and init object """
        # extract logs from all objects
        combined_log = combine_logs(objects, id_map=id_map)
        # reshape into set of activities with start, duration and end
        super_log = reshape_superlog(combined_log)
        # add unique identifier for activities (may be shared by multiple objects)
        super_log = add_unique_activity(super_log)
        return cls(df_super_log=super_log)


def reshape_superlog(super_log):
    """
    function to reshape superlog to activity with start and
    end times in 1 row (rather than row starts and rows stop

    Parameters
    ------------
    super_log : pd.DataFrame()
        format like return from combine_logs() or plot.get_log_dataframe() function defs

    Returns
    ---------
    df_new : pd.DataFrame()
        like input but start and endtime on single row
    """
    super_log = super_log.sort_values(by=["Timestamp", "ActivityState"])  # keep df chronological!!
    super_log = super_log.reset_index()
    to_handle = list(range(0, len(super_log)))
    df_new = pd.DataFrame()
    safety_valve = 0
    while len(to_handle) > 0 and safety_valve < len(super_log):
        safety_valve += 1
        idx_start = to_handle[0]
        row_current = super_log.loc[idx_start, :]
        if row_current.loc['ActivityState'] not in ['START', 'WAIT_START']:
            raise ValueError(f"Unexpected starting state {row_current.loc['ActivityState']} "
                             f"for idx {idx_start}, so skipping this")

        bool_candidates = (super_log.loc[:, "Activity"] == row_current.loc['Activity']) & \
                          (super_log.loc[:, "SourceObject"] == row_current.loc['SourceObject']) & \
                          (super_log.loc[:, "ActivityState"].isin(['STOP', 'WAIT_STOP']))
        idx_candidates = list(bool_candidates.index[bool_candidates])
        idx_end = [idx_end for idx_end in idx_candidates if idx_end > idx_start and idx_end in to_handle][0]
        # now remove idx start and end from handle
        to_handle.remove(idx_start)
        to_handle.remove(idx_end)
        # and place in new dataframe
        df_new = pd.concat([df_new, pd.DataFrame({"Activity": row_current.loc['Activity'],
                                                  "SourceObject": row_current.loc['SourceObject'],
                                                  "start_time": row_current.loc['Timestamp'],
                                                  "state": "WAITING" if "WAIT" in row_current.loc[
                                                      'ActivityState'] else "ACTIVE",
                                                  "duration": super_log.loc[idx_end, "Timestamp"] - row_current.loc[
                                                      'Timestamp'],
                                                  "end_time": super_log.loc[idx_end, "Timestamp"]}, index=[0])],
                           ignore_index=True, sort=False)
    # ASSUME that activities with duration zero can be discarded
    df_new = df_new.loc[df_new.loc[:, "duration"] > 0, :]

    assert len(to_handle) == 0, f"These have not been handled {to_handle}"
    df_new = df_new.sort_values(by=["start_time", "SourceObject"])
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
        has proper coolumns for input/init SuperLog
    """
    unique_combis = df_new.groupby(['Activity', 'start_time', 'end_time']).\
        size().reset_index().rename(columns={0: 'count'})
    # now add unique ID to df_new
    for idx, row in unique_combis.iterrows():
        bool_match = (df_new.loc[:, "Activity"] == row.loc["Activity"]) & \
                     (df_new.loc[:, "start_time"] == row.loc["start_time"]) & \
                     (df_new.loc[:, "end_time"] == row.loc["end_time"])
        df_new.loc[bool_match, "cp_activity_id"] = f"cp_activity_{idx+1}"

    return df_new


def combine_logs(objects, id_map=None):
    """
    Combines the logs of given objects into a single dataframe.

    Parameters
    ------------
    objects : list
        a list of vessels, sites for which to plot all activities. These need to have had logging!
    id_map : list or dict
         * a list of top-activities of which also all sub-activities
          will be resolved, e.g.: [while_activity]
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}
    """
    # check unique names
    names = [obj.name for obj in objects]
    assert len(names) == len(set(names)), 'Names of your objects must be unique!'

    # concat
    log_all = pd.DataFrame()
    for obj in objects:
        log = plot.get_log_dataframe(obj, id_map)
        log['SourceObject'] = obj.name

        log_all = pd.concat([log_all, log])

    return log_all.sort_values('Timestamp').reset_index(drop=True)


def get_superlog_with_critical_path(list_objects, id_map):
    """
    main function to get 1 dataframe with all logged activities marked by 'is_critical'

    Parameters
    ------------
    list_objects : list
        a list of vessels, sites for which to plot all activities. These need to have had logging!
    id_map : list or dict
         * a list of top-activities of which also all sub-activities
          will be resolved, e.g.: [while_activity]
        * a manual id_map to resolve uuids to labels, e.g. {'uuid1':'name1'}
    """
    my_superlog = SuperLog.from_objects(list_objects, id_map)
    my_graph = ActivityGraph(my_superlog.df_super_log, my_superlog.dependencies)
    list_actvities_critical = my_graph.mark_critical_activities()
    # also test plot - also takes time
    log_out = my_superlog.df_super_log.copy()
    log_out.loc[:, 'is_critical'] = log_out.loc[:, 'cp_activity_id'].isin(list_actvities_critical)
    return log_out