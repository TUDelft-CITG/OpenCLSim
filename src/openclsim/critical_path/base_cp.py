"""
Module with BaseCp class that has (non-abstract) methods wrt finding
the critical path of the simulation

"""

import uuid
from abc import ABC, abstractmethod

import pandas as pd
import plotly.graph_objs as go

from openclsim.critical_path.simulation_graph import SimulationGraph
from openclsim.model import get_subprocesses
from openclsim.plot.log_dataframe import get_log_dataframe
from openclsim.plot.vessel_planning import add_layout_gantt_chart, get_colors


class BaseCP(ABC):
    """
    Base class for critical path

    Parameters
    ------------
    env : simpy.Environment
        instance of simpy.env or instance of class that inherits from simpy.env
    object_list : list
        list of all (simulation) objects with Log mixin (after simulation)
    activity_list : list
        list of all (simulation) activities with Log mixin (after simulation)
    """

    def __init__(
        self,
        env,
        object_list,
        activity_list,
        *args,
        **kwargs,
    ):
        """
        Init.
        """
        super().__init__(*args, **kwargs)

        # set to self
        self.env = env
        self.object_list = object_list
        self.activity_list = activity_list

        # init attributes which will be set by (child) methods
        self.recorded_activities_df = None
        self.critical_path_df = None
        self.dependency_list = None
        self.simulation_graph = None

    @abstractmethod
    def get_dependency_list(self):
        """
        Must be implemented by child classes

        Returns
        -------
        dependency_list : list
            list of tuples (dependencies)
        """
        return []

    def _make_recorded_activities_df(self):
        """
        Set a recorded_activity_df in self.
        Uses the logs of provided activities and sim objects, combines these, adds unique UUID
        and reshape into format such that single row has a start time and an end time.
        """

        # get all recorded events through logs simulation objects (excl plugins)
        all_recorded_events_objects = self.combine_logs()

        # get all recorded events through logs activities
        # (incl plugins, start/condition events etc.)
        all_recorded_events_activities = self.get_log_dataframe_activity(
            get_subprocesses(self.activity_list)
        )

        all_recorded_events = pd.concat(
            [all_recorded_events_objects, all_recorded_events_activities]
        ).reset_index(drop=True)

        # reshape into set of activities with start, duration and end
        recorded_activities_df = self.reshape_log(all_recorded_events)

        # add unique identifier for activities (could be shared by multiple objects)
        recorded_activities_df = self.add_unique_activity(recorded_activities_df)

        self.recorded_activities_df = recorded_activities_df.sort_values(
            by=["start_time", "Activity", "SimulationObject"]
        ).reset_index(drop=True)

    def combine_logs(self):
        """
        Combines the logs of given (simulation) objects into a single pandas.Dataframe.
        """
        # check unique names
        names = [obj.name for obj in self.object_list]
        if not len(names) == len(set(names)):
            raise ValueError("Names of your objects must be unique!")

        # concat logs with name and keep only columns needed
        log_list = [get_log_dataframe(obj) for obj in self.object_list]
        names_column = (
            pd.Series(names, name="SimulationObject")
            .repeat([len(df) for df in log_list])
            .reset_index(drop=True)
        )
        log_all = pd.concat(
            [names_column, pd.concat(log_list).reset_index(drop=True)], axis=1
        )
        log_all = log_all[
            ["Activity", "Timestamp", "ActivityState", "SimulationObject"]
        ]

        # keep ID and name (for readability)
        list_all_activities = get_subprocesses(self.activity_list)
        id_map = {act.id: act.name for act in list_all_activities}
        log_all["ActivityID"] = log_all["Activity"]
        log_all["Activity"] = log_all["Activity"].replace(id_map)

        return log_all.sort_values("Timestamp").reset_index(drop=True)

    @staticmethod
    def get_log_dataframe_activity(activity_list):
        """
        Get the log of the activity object in a pandas dataframe.

        Parameters
        ----------
        activity_list : list
            list of recorded activities, i.e. every activity has log attribute.
        """

        id_map = {act.id: act.name for act in activity_list}

        all_dfs_list = []
        for sub_activity in activity_list:
            all_dfs_list.append(sub_activity.log)

        all_timestamps = [ts for dict_ in all_dfs_list for ts in dict_["Timestamp"]]
        all_activity_id = [id_ for dict_ in all_dfs_list for id_ in dict_["ActivityID"]]
        all_states = [
            state for dict_ in all_dfs_list for state in dict_["ActivityState"]
        ]
        df_all = pd.DataFrame(
            {
                "ActivityID": all_activity_id,
                "Timestamp": all_timestamps,
                "ActivityState": all_states,
                "Activity": [id_map[id_] for id_ in all_activity_id],
                "SimulationObject": "Activity",
            }
        )

        return df_all

    @staticmethod
    def reshape_log(df_log):
        """
        Reshape OpenCLSim log to a workable format for extracting critical path.

        This function reshapes a log DataFrame as output from OpenCLSim such that
        an activity appears with a single log-line. The start and end times of the
        activity is added in new columns.

        Parameters
        ----------
        df_log : pd.DataFrame
            Format like return from self.combine_logs() or plot.get_log_dataframe().

        Returns
        -------
        recorded_activities_df : pd.DataFrame
            The reformatted and reshaped log.
        """

        df_log = df_log.sort_values(
            by=["ActivityID", "Timestamp", "ActivityState"]
        ).reset_index()

        df_starts = (
            df_log[df_log.ActivityState.isin(["START", "WAIT_START"])]
            .filter(
                [
                    "ActivityID",
                    "Activity",
                    "SimulationObject",
                    "Timestamp",
                    "ActivityState",
                ]
            )
            .rename(columns={"Timestamp": "start_time"})
            .set_index("ActivityID")
        )
        df_stops = (
            df_log[df_log.ActivityState.isin(["STOP", "WAIT_STOP"])]
            .filter(["ActivityID", "Timestamp"])
            .rename(columns={"Timestamp": "end_time"})
            .set_index("ActivityID")
        )
        recorded_activities_df = (
            pd.concat([df_starts, df_stops], axis=1)
            .sort_values(by=["start_time"])
            .reset_index()
        )

        recorded_activities_df["duration"] = (
            recorded_activities_df.end_time - recorded_activities_df.start_time
        )
        recorded_activities_df["state"] = recorded_activities_df.apply(
            lambda x: "WAITING" if "WAIT" in x["ActivityState"] else "ACTIVE", axis=1
        )

        recorded_activities_df = recorded_activities_df.drop(columns=["ActivityState"])

        return recorded_activities_df

    @staticmethod
    def add_unique_activity(recorded_activities_df):
        """
        Add a unique activity ID in time.

        OpenCLSim activities have their unique UUID. However, if the same activity
        is executed serveral times in through time, the same ID will appear in the
        log. For the analysis of the critical path of executed activities, it is
        desired to make the distinction between _activity A_ starting at time _t1_,
        and the same _activity A_ starting at time _t2_. This new ID is added as
        an additional column in the provided log as ``cp_activity_id``.

        Parameters
        -----------
        recorded_activities_df : pd.DataFrame
            Columns/format like return from self.reshape_log().

        Returns
        ----------
        recorded_activities_df : pd.DataFrame
            As input, with additional column `cp_activity_id`.
        """
        # add unique identifier (count) based on activity ID and time, and then set to UUID
        recorded_activities_df.insert(
            loc=len(recorded_activities_df.columns),
            column="cp_activity_id",
            value=recorded_activities_df.set_index(
                ["ActivityID", "start_time", "end_time"]
            ).index.factorize()[0],
        )
        mapping = {
            temp_id: str(uuid.uuid4())
            for temp_id in recorded_activities_df["cp_activity_id"]
        }
        recorded_activities_df["cp_activity_id"] = recorded_activities_df[
            "cp_activity_id"
        ].apply(lambda x: mapping[x])

        return recorded_activities_df

    def get_recorded_activity_df(self):
        """
        Get a recorded_activity_df from self.

        Returns
        -------
        recorded_activity_df : pd.DataFrame
            All recorded activities from simulation.
        """
        if self.recorded_activities_df is None:
            self._make_recorded_activities_df()
        return self.recorded_activities_df

    def __make_simulation_graph(self):
        """
        Use self.recorded_activity_df and self.dependency_list to build graph of
        (interconnected) activities as evaluated in time in simulation.
        """
        self.simulation_graph = SimulationGraph(
            self.recorded_activities_df, self.dependency_list
        )

    def get_critical_path_df(self):
        """
        Enrich recorded activity df with column 'is_critical' and return this dataframe.

        Returns
        -------
        recorded_activity_df : pd.DataFrame
            All recorded activities from simulation.
        """
        if self.critical_path_df is None:
            self._set_critical_path_df()

        return self.critical_path_df

    def _set_critical_path_df(self):
        """Set critical_path_df."""
        self.get_recorded_activity_df()
        self.get_dependency_list()
        self.__make_simulation_graph()
        self.critical_path_df = self.__compute_critical_path()

    def __compute_critical_path(self):
        """
        Provided self has a simulation graph based on all the recorded activities and
        dependencies, compute the critical path, i.e. mark all activities which are on (any)
        critical path as critical.

        Returns
        -------
        critical_path_df : pd.DataFrame
            Recorded activities from simulation for visualisation
            critical path (in pd.DataFrame or plot).
        """
        critical_activities = self.simulation_graph.get_list_critical_activities()
        recorded_activity_df = self.get_recorded_activity_df().copy()
        recorded_activity_df["is_critical"] = recorded_activity_df[
            "cp_activity_id"
        ].isin(critical_activities)

        # remove activities which are duplicate or irrelevant
        critical_path_df = self._remove_duplicate_activities(recorded_activity_df)

        return critical_path_df

    @staticmethod
    def _remove_duplicate_activities(recorded_activities_df):
        """
        This method removes duplicate activities within recorded_activities_df,
        i.e. activities which also have been recorded with one or more
        simulation objects (vessel, site).

        Parameters
        ----------
        recorded_activities_df : pd.DataFrame
            Recorded activities, containing duplicate cp_activity_id's
            for 'Activity' and simulation objects.

        Returns
        -------
        critical_path_df : pd.DataFrame
            Recorded activities, containing NO duplicate cp_activity_id's
            for 'Activity' and simulation objects.
        """
        # cp_activity IDs for both an activity
        # and another simulation objects are too much - filter out
        df_no_activity = recorded_activities_df.loc[
            recorded_activities_df.SimulationObject != "Activity", :
        ]
        df_to_add = recorded_activities_df.loc[
            (
                (recorded_activities_df.SimulationObject == "Activity")
                & recorded_activities_df.is_critical
                & (
                    ~recorded_activities_df.cp_activity_id.isin(
                        df_no_activity.cp_activity_id
                    )
                )
            ),
            :,
        ]
        critical_path_df = pd.concat([df_no_activity, df_to_add])

        return critical_path_df

    def make_plotly_gantt_chart(self, static=False):
        """
        Make plotly gantt chart with critical path included (marked as red).
        The figure will contain a 'row' for each simulation object,
        and on each row horizontal bars that indicate an activity in time.

        Parameters
        ----------
        static : boolean
            If True a dict is returned (for use in go.Figure()).
            If False then this figure is returned with iplot.
        """
        critical_path_dataframe = self.get_critical_path_df()

        default_blockwidth = 10
        # prepare traces for each of the activities
        traces = []
        if critical_path_dataframe is not None:
            x_critical = critical_path_dataframe.loc[
                critical_path_dataframe.loc[:, "is_critical"], "start_time"
            ].tolist()

            x_critical_end = critical_path_dataframe.loc[
                critical_path_dataframe.loc[:, "is_critical"], "end_time"
            ].tolist()

            ylist = critical_path_dataframe.loc[
                critical_path_dataframe.loc[:, "is_critical"], "SimulationObject"
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
                    line=dict(color="red", width=default_blockwidth + 4),
                    connectgaps=False,
                )
            )

        # unique combis of activity and simulation type
        plot_combis = (
            critical_path_dataframe.loc[:, ["SimulationObject", "Activity"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        C = get_colors(len(plot_combis))
        colors = {}
        for i in range(len(plot_combis)):
            colors[i] = f"rgb({C[i][0]},{C[i][1]},{C[i][2]})"

        for plot_combi in plot_combis.itertuples():
            bool_this_combi = (
                critical_path_dataframe.SimulationObject == plot_combi.SimulationObject
            ) & (critical_path_dataframe.Activity == plot_combi.Activity)
            # now activities with name
            x_critical = critical_path_dataframe.loc[
                bool_this_combi, "start_time"
            ].tolist()
            x_critical_end = critical_path_dataframe.loc[
                bool_this_combi, "end_time"
            ].tolist()

            ylist = critical_path_dataframe.loc[
                bool_this_combi, "SimulationObject"
            ].tolist()

            x_nest = [[x1, x2, x2] for (x1, x2) in zip(x_critical, x_critical_end)]
            y_nest = [[y, y, None] for y in ylist]

            traces.append(
                go.Scatter(
                    name=f"{plot_combi.Activity}",
                    x=[item for sublist in x_nest for item in sublist],
                    y=[item for sublist in y_nest for item in sublist],
                    mode="lines",
                    hoverinfo="y+name",
                    line=dict(color=colors[plot_combi.Index], width=default_blockwidth),
                    connectgaps=False,
                )
            )

        return add_layout_gantt_chart(
            traces,
            critical_path_dataframe.start_time.min(),
            critical_path_dataframe.end_time.max(),
            static=static,
        )
