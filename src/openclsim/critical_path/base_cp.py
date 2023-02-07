"""
Module with BaseCp class that has (non-abstract) methods wrt finding
the critical path of the simulation

"""

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
        # check unique names
        names = [obj.name for obj in self.object_list]
        if not len(names) == len(set(names)):
            raise ValueError("Names of your objects must be unique!")

        # concat with name
        log_list = [get_log_dataframe(obj) for obj in self.object_list]
        names_column = pd.Series(names, name="SimulationObject").repeat(
            [len(df) for df in log_list]).reset_index(drop=True)
        log_all = pd.concat([names_column, pd.concat(log_list).reset_index(drop=True)], axis=1)

        # keep only columns directly needed
        log_all = log_all[
            ["Activity", "Timestamp", "ActivityState", "SimulationObject"]
        ]

        # keep ID and add name for us humans
        list_all_activities = get_subprocesses(self.activity_list)
        id_map = {act.id: act.name for act in list_all_activities}
        log_all["ActivityID"] = log_all["Activity"]
        log_all["Activity"] = log_all["Activity"].replace(id_map)

        return log_all.sort_values("Timestamp").reset_index(drop=True)

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
