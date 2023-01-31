"""
Module with BaseCp class that has (non-abstract) methods wrt finding
the critical path of the simulation

"""

import datetime as dt
import uuid
from abc import ABC, abstractmethod

import pandas as pd

from openclsim.critical_path.simulation_graph import SimulationGraph
from openclsim.model import get_subprocesses
from openclsim.plot.log_dataframe import get_log_dataframe


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

        # some asserts todo

        # set to self
        self.env = env
        self.object_list = object_list
        self.activity_list = activity_list

        # init attributes which will be set by (child) methods
        self.recorded_activities_df = None
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
        # get all recorded log-events
        all_recorded_events = self.combine_logs()

        # reshape into set of activities with start, duration and end
        recorded_activities_df = self.reshape_log(all_recorded_events)

        # add unique identifier for activities (could be shared by multiple objects)
        self.recorded_activities_df = self.add_unique_activity(recorded_activities_df)

    def combine_logs(self):
        """
        Combines the logs of given (simulation) objects into a single pandas.Dataframe.
        """
        # check unique names - @Pieter maybe warning?
        names = [obj.name for obj in self.object_list]
        if not len(names) == len(set(names)):
            raise ValueError("Names of your objects must be unique!")

        # concat
        log_all = pd.DataFrame()
        for obj in self.object_list:
            log = get_log_dataframe(obj)
            log["SimulationObject"] = obj.name
            log_all = pd.concat([log_all, log])

        # keep only columns directly needed
        log_all = log_all.loc[
            :, ["Activity", "Timestamp", "ActivityState", "SimulationObject"]
        ]

        # keep ID and add name for us humans
        log_all.loc[:, "ActivityID"] = log_all.loc[:, "Activity"]
        list_all_activities = get_subprocesses(self.activity_list)
        id_map = {act.id: act.name for act in list_all_activities}
        log_all.loc[:, "Activity"] = log_all.loc[:, "Activity"].replace(id_map)

        return log_all.sort_values("Timestamp").reset_index(drop=True)

    @staticmethod
    def reshape_log(df_log):
        """
        Reshape OpenCLSim log to a workable format for extracting critical path.

        This function reshapes a log DataFrame as output from OpenCLSim such that
        an activity appears with a single log-line. The start and end times of the
        activity is added in new columns.

        Note: the function starts off with a start event of an activity, and then
        selects the stop event which is closest after this start event. It assumes
        that activities with duration zero can be discarded.

        Parameters
        ----------
        df_log : pd.DataFrame
            Format like return from self.combine_logs() or plot.get_log_dataframe().

        Returns
        -------
        recorded_activities_df : pd.DataFrame
            The reformated and reshaped log.
        """
        # keep the df chronological
        df_log = df_log.sort_values(by=["Timestamp", "ActivityState"])
        df_log = df_log.reset_index()

        # make a list of indexes to handle
        to_handle = list(range(0, len(df_log)))

        # init the output
        recorded_activities_df = pd.DataFrame()

        # loop exit
        safety_valve = 0
        while (len(to_handle) > 0) and (safety_valve < len(df_log)):
            # update the safety valve
            safety_valve += 1

            # select a log-row to inspect
            idx_start = to_handle[0]
            row_current = df_log.loc[idx_start, :]

            # check for a start event
            if row_current.loc["ActivityState"] not in ["START", "WAIT_START"]:
                raise ValueError(
                    f"Unexpected starting state {row_current.loc['ActivityState']}"
                    f" for idx {idx_start}, so skipping this."
                )

            # see what stop events could belong to this start event
            bool_candidates = (
                (df_log.loc[:, "ActivityID"] == row_current.loc["ActivityID"])
                & (
                    df_log.loc[:, "SimulationObject"]
                    == row_current.loc["SimulationObject"]
                )
                & (df_log.loc[:, "ActivityState"].isin(["STOP", "WAIT_STOP"]))
            )
            idx_candidates = list(bool_candidates.index[bool_candidates])
            # select the first end event after the start event
            idx_end = [
                idx_end
                for idx_end in idx_candidates
                if idx_end > idx_start and idx_end in to_handle
            ][0]

            # now remove idx start and end from handle
            to_handle.remove(idx_start)
            to_handle.remove(idx_end)

            # and place in new dataframe
            recorded_activities_df = pd.concat(
                [
                    recorded_activities_df,
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
        if isinstance(recorded_activities_df.loc[:, "duration"][0], dt.timedelta):
            recorded_activities_df = recorded_activities_df.loc[
                recorded_activities_df.loc[:, "duration"] > dt.timedelta(seconds=0), :
            ]
        else:
            recorded_activities_df = recorded_activities_df.loc[
                recorded_activities_df.loc[:, "duration"] > 0, :
            ]

        assert len(to_handle) == 0, f"These have not been handled {to_handle}"
        recorded_activities_df = recorded_activities_df.sort_values(
            by=["start_time", "SimulationObject"]
        )
        recorded_activities_df = recorded_activities_df.reset_index(drop=True)

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
        unique_combis = (
            recorded_activities_df.groupby(["ActivityID", "start_time", "end_time"])
            .size()
            .reset_index()
            .rename(columns={0: "count"})
        )
        # now add unique ID to df_new
        for idx, row in unique_combis.iterrows():
            bool_match = (
                (recorded_activities_df.loc[:, "ActivityID"] == row.loc["ActivityID"])
                & (recorded_activities_df.loc[:, "start_time"] == row.loc["start_time"])
                & (recorded_activities_df.loc[:, "end_time"] == row.loc["end_time"])
            )
            recorded_activities_df.loc[bool_match, "cp_activity_id"] = str(uuid.uuid4())

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
        (interconnected) activities as evaluated in time in simulation
        """
        self.simulation_graph = SimulationGraph(
            self.recorded_activities_df, self.dependency_list
        )

    def get_critical_path_df(self):
        """
        Enrich recorded activity df with column 'is_critical' and return this dataframe

        Returns
        -------
        recorded_activity_df : pd.DataFrame
            All recorded activities from simulation.
        """
        self._make_recorded_activities_df()
        self.dependency_list = self.get_dependency_list()
        self.__make_simulation_graph()

        return self.__compute_critical_path()

    def __compute_critical_path(self):
        """
        Provided self has a simulation graph based on all the recorded activities and
        dependencies, compute the critical path, i.e. mark all activities which are on (any)
        critical path as critical.

        Returns
        -------
        recorded_activity_df : pd.DataFrame
            All recorded activities from simulation.
        """
        return pd.DataFrame()
