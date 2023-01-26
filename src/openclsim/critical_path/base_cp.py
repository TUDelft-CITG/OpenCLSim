"""
Module with BaseCp class that has (non-abstract) methods wrt finding
the critical path of the simulation

"""

from abc import ABC, abstractmethod

import pandas as pd

from openclsim.critical_path.simulation_graph import SimulationGraph


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
        and reshape into format such that single row has a start time and an end time
        """
        pass

    def get_recorded_activity_df(self):
        """
        Get a recorded_activity_df from self.

        Returns
        -------
        recorded_activity_df : pd.DataFrame
            all recorded activities from simulation
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
            all recorded activities from simulation.
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
            all recorded activities from simulation.
        """
        return pd.DataFrame()
