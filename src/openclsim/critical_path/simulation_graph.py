"""
Module that contains class SimulationGraph.
SimulationGraph is a graph representation of simulated activities and their dependencies.
"""

import copy
import datetime as dt
import logging

import networkx as nx
from pandas.api.types import is_numeric_dtype, is_timedelta64_dtype


class SimulationGraph:
    """
    Graph representation of simulated activities and their dependencies.

    Class to construct a ``networkx.DiGraph`` from simulation activity logs
    captured in a CpLog-object, and corresponding dependencies between those
    activities. Simulated activities appear in the graph as sets of _node-edge-
    node_, with a start time, end time and a duration. Dependencies between
    activities are added through connecting edges, from the end-node of one
    activity, to the starting-node of the next activity.

    Durations linked to activity-edges make up the basis for finding the
    critical path of the simulated process. In essence, the critical path
    is the path through the activities of longest duration. Hence, it are those
    edges in the graph which are on a path of longest duration.

    Correct identification of dependencies between activities ensure proper
    path definitions in the graph. Note that finding the critical path(s)
    relies strongly on finding the correct dependencies between activities.

    Parameters
    ----------
    recorded_activities_df : pd.DataFrame
        attribute from instance of BaseCpLog
    dependency_list : list
        A key part of the recorded_activities_df is the ``cp_activity_id`` column. This column
        contains unique identifyers for simulated activities in time. This list
        is to contain tuples of those IDs defining dependencies between the
        corresponding activities. E.g. if the completion of activity with
        ``id==1`` triggers the start of activity with ``id==2``, then this
        should appear in the list as tuple ``(1, 2)``.
    """

    # name of added columns to the recorded_activities_df
    __COLNAME_CRITICAL = "is_critical"

    # mapping from column name to attribute
    __RECORDED_ACTIVITY_COLUMNS = {
        "Activity": "activity",
        "SimulationObject": "source_object",
        "start_time": "start_time",
        "state": "state",
        "duration": "duration",
        "end_time": "end_time",
        "cp_activity_id": "cp_activity_id",
    }

    # fixed edge types
    __EDGE_TYPES = {0: "activity", 1: "dependency"}

    # criticality
    __CRITICAL = {0: False, 1: True}

    # prefixes to use for node start and end
    __NODE_START_PREFIX = "start"
    __NODE_END_PREFIX = "end"

    def __init__(self, recorded_activities_df, dependency_list):
        """Initialize the object."""
        self.critical_edges_list = None
        self.recorded_activities_df = self.__check_recorded_activities_df(
            recorded_activities_df
        )
        self.dependency_list = self.__check_dependency_list(dependency_list)

        # construct the graph based on the log and dependencies
        self.simulation_graph = self.__construct_graph()

        self.n_activities = len(
            [
                e
                for e in self.simulation_graph.edges
                if self.simulation_graph.edges[e]["edge_type"] == "activity"
            ]
        )

        # get the duration of longest path
        self.max_duration = nx.dag_longest_path_length(
            self.simulation_graph, weight="duration"
        )

    def __check_recorded_activities_df(self, recorded_activities_df):
        """
        Check validity of recorded_activities_df.

        Parameters
        ----------
        recorded_activities_df : pd.DataFrame
            attribute from instance of BaseCpLog
        """
        # check expected columns
        missing_columns = [
            c
            for c in self.__RECORDED_ACTIVITY_COLUMNS.keys()
            if c not in recorded_activities_df.columns
        ]
        assert missing_columns == [], f"cp_log is missing columns {missing_columns}"

        return self.__prepare_recorded_activities_df(recorded_activities_df)

    def __prepare_recorded_activities_df(self, recorded_activities_df):
        """
        Prepare the recorded_activities_df to a workable format.

        Makes sure that column names are standardized, and that durations of
        activities are presented in seconds.
        """
        # rename columns to class defaults
        recorded_activities_df = recorded_activities_df.rename(
            columns=self.__RECORDED_ACTIVITY_COLUMNS
        )

        # make sure the duration is numeric
        recorded_activities_df["duration"] = (
            recorded_activities_df["end_time"] - recorded_activities_df["start_time"]
        )
        if is_timedelta64_dtype(recorded_activities_df["duration"]):
            logging.debug("Converting duration to seconds (float)")
            recorded_activities_df["duration"] = round(
                recorded_activities_df["duration"].dt.total_seconds(), 3
            )
        if not is_numeric_dtype(recorded_activities_df["duration"]):
            raise TypeError(
                f"Duration computed as type {type(recorded_activities_df['duration'][0])} "
                "is not supported!"
            )

        # drop activities with zero time, they mess up algorithm
        recorded_activities_df = recorded_activities_df.loc[
            recorded_activities_df.duration != 0, :
        ]
        # make sure all durations are positive
        if not all(recorded_activities_df["duration"] > 0):
            raise ValueError("Negative durations encountered in activities.")

        return recorded_activities_df

    def __check_dependency_list(self, dependency_list):
        """
        Check validity of dependency_list.

        Parameters
        ----------
        dependency_list : list
        """
        assert isinstance(dependency_list, list), "list_dependencies must be a list"

        dependency_list = [
            (f"{self.__NODE_END_PREFIX} {end}", f"{self.__NODE_START_PREFIX} {start}")
            for end, start in dependency_list
        ]
        return dependency_list

    def __construct_graph(self):
        """
        Construct and return simulation graph (self.simulation_graph),
        the networkx diGraph representing the OpenClSim simulation,
        so including all recorded activities and their dependencies (in time).

        Returns
        -------
        simulation_graph : nx.DiGraph
            the networkx diGraph representing the OpenClSim simulation
        """
        self.simulation_graph = nx.DiGraph()

        self.__create_activity_edges()
        self.__link_activity_edges()

        # check if the resulting graph is acyclic
        assert nx.is_directed_acyclic_graph(
            self.simulation_graph
        ), "The resulting graph appears to be cyclic!"

        return self.simulation_graph

    def __create_activity_edges(self):
        """
        Create nodes and edges for each individual activity.

        Converts all cp_activity_ids within ``self.recorded_activities_df``
        into start and end nodes connected through an edge.
        All relevant attributes, such as the duration of an activity,
        are added to these nodes and edges.
        """
        cp_activities_df = self.recorded_activities_df.drop_duplicates(
            subset=["cp_activity_id"]
        )
        for params in cp_activities_df.itertuples():
            # names of the nodes by start/end of
            name_start = f"{self.__NODE_START_PREFIX} {params.cp_activity_id}"
            name_end = f"{self.__NODE_END_PREFIX} {params.cp_activity_id}"

            # add the start node
            self.simulation_graph.add_node(
                name_start,
                time=params.start_time,
                cp_activity_id=params.cp_activity_id,
            )

            # add the end node
            self.simulation_graph.add_node(
                name_end,
                time=params.end_time,
                cp_activity_id=params.cp_activity_id,
            )

            # add the edge
            kwargs = {
                "node_start": name_start,
                "node_end": name_end,
                "activity": params.activity,
                "start_time": params.start_time,
                "state": params.state,
                "duration": params.duration,
                "end_time": params.end_time,
                "cp_activity_id": params.cp_activity_id,
                "edge_type": self.__EDGE_TYPES[0],
                self.__COLNAME_CRITICAL: self.__CRITICAL[0],
            }
            self.simulation_graph.add_edge(name_start, name_end, **kwargs)

    def __link_activity_edges(self):
        """
        Add connecting edges between linked activities.

        Note: this method is to be called after ``self.__create_activity_edges()``.

        Uses the ``self.list_dependencies`` to link all loose nodes and edges
        together within the graph. Note that edges are added from the END of
        the first activity (dependency cause) to the START of the second (dependency effect).
        """
        for dependency_cause, dependency_effect in self.dependency_list:
            # extract some information on the times
            start_time = self.simulation_graph.nodes[dependency_cause]["time"]
            end_time = self.simulation_graph.nodes[dependency_effect]["time"]
            duration = end_time - start_time

            if isinstance(duration, dt.timedelta):
                duration = int(duration.total_seconds())
            if not isinstance(duration, (float, int)):
                raise TypeError(
                    f"Duration computed as type {duration} " "is not supported!"
                )
            if round(duration, 4) != 0:
                raise ValueError(
                    f"dependency ({dependency_cause}, {dependency_effect})"
                    f" with non zero duration ({duration}) not allowed!"
                )
            # add the edge from cause to effect
            edge_kwargs = {
                "node_start": dependency_cause,
                "node_end": dependency_effect,
                "activity": None,
                "start_time": start_time,
                "state": None,
                "duration": duration,
                "end_time": end_time,
                "cp_activity_id": None,
                "edge_type": self.__EDGE_TYPES[1],
                self.__COLNAME_CRITICAL: self.__CRITICAL[0],
            }
            self.simulation_graph.add_edge(
                dependency_cause, dependency_effect, **edge_kwargs
            )

    def __find_critical_edges(
        self,
        marked_edges_graph=None,
        list_critical=None,
        list_noncritical=None,
        to_discount=None,
        max_duration=None,
        t_max_end=None,
        duration_discounted_prev=None,
    ):
        """
        Create a list of edges on a longest path in the graph (recursively).

        This method recursively builds a list of edges in the activity graph
        which are on the longest path. In a nutshell the process is as follows:

        0. Create a shadow/copy of the activity graph 'marked_edges_graph'.
        1. Find an initial longest path, mark all edges on it as such, and set
           their 'duration' to 10**-4 on the shadow-graph (i.e. discount all
           edges which have already been marked).
        2. Find a new longest path in the shadow-graph, and check if the
           duration in the original graph equals the maximum length. If so,
           good! Mark all edges as critical and set duration in the shadow
           graph to 10**-4. If not a feasible longest path, then mark the last
           edge as noncritical, and set its weight in the shadow graph to
           10**-8.
        3. Repeat until all edges are marked as critical or non-critical.
        """

        feasible_longest = False  # all edges on path can be discounted at once

        # the initial iteration
        if marked_edges_graph is None:
            # make a copy of the graph to change weights
            marked_edges_graph = copy.deepcopy(self.simulation_graph)

            # get an initial longest path
            longest_path = nx.dag_longest_path(self.simulation_graph, weight="duration")
            list_critical = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.simulation_graph.edges[i]["edge_type"] == "activity"
            ]
            logging.debug(f"Found initial longest path {list_critical}.")

            # get the end time of the initial longest path
            t_start = self.simulation_graph.nodes[longest_path[0]]["time"]
            t_max_end = self.simulation_graph.nodes[longest_path[-1]]["time"]

            logging.debug(
                f"Max duration {round(self.max_duration, 2)}, "
                f"t_start {t_start} and t_max end {t_max_end}."
            )

            # ready to continue
            list_noncritical = []
            to_discount = []
            feasible_longest = True

        # any following iteration
        else:
            # get the current longest path in the discount graph
            longest_path = nx.dag_longest_path(marked_edges_graph, weight="duration")
            lp_edges = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.simulation_graph.edges[i]["edge_type"] == "activity"
            ]

            # get the original duration
            lp_duration_discounted = nx.path_weight(
                marked_edges_graph, longest_path, weight="duration"
            )
            lp_duration = round(
                nx.path_weight(self.simulation_graph, longest_path, weight="duration"),
                2,
            )
            t_start = self.simulation_graph.nodes[longest_path[0]]["time"]
            t_end = self.simulation_graph.nodes[longest_path[-1]]["time"]
            logging.debug(
                f"longest path found: duration {lp_duration}, t_start "
                f"{t_start} and t_end {t_end}. (discounted duration "
                f"{lp_duration_discounted})"
            )

            # see if this path is a feasible longest path in the original
            # i.e. must be max duration and same end time
            new_cp = (lp_duration == round(self.max_duration, 2)) and (
                t_end == t_max_end
            )
            if new_cp:
                # create list of not-yet-marked-as-critical critical edges
                to_add_critical = [
                    edge for edge in lp_edges if edge not in list_critical
                ]
                logging.debug(
                    "New elements on critical path path, " f"adding {to_add_critical}."
                )
                list_critical += to_add_critical
                feasible_longest = True
            else:
                to_add_discount = [edge for edge in lp_edges if edge not in to_discount]
                logging.debug("adding to discount")
                to_discount += to_add_discount

        # discount the edges, all at once, or only the last one
        if feasible_longest:
            logging.debug("discounting all")
            # in one go discount all activity edges in critical path
            list_edges = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.simulation_graph.edges[i]["edge_type"] == "activity"
            ]
            for edge in list_edges:
                marked_edges_graph.edges[edge]["duration"] = 10**-4
                self.simulation_graph.edges[edge][self.__COLNAME_CRITICAL] = (
                    self.__CRITICAL[1]
                )
            yet_to_discount = []
        else:
            yet_to_discount = [
                edge for edge in to_discount if edge not in list_noncritical
            ]
            if len(yet_to_discount) > 0:
                logging.debug(f"Discounting {yet_to_discount[-1]}")
                marked_edges_graph.edges[yet_to_discount[-1]]["duration"] = 10**-8
                list_noncritical.append(yet_to_discount[-1])
                yet_to_discount = yet_to_discount[:-1]

        # iterate if we have yet to discount or if we have marked all edges
        if len(list_critical) + len(list_noncritical) == self.n_activities:
            return list_critical
        return self.__find_critical_edges(
            marked_edges_graph=marked_edges_graph,
            list_critical=list_critical,
            list_noncritical=list_noncritical,
            to_discount=yet_to_discount,
            max_duration=max_duration,
            t_max_end=t_max_end,
            duration_discounted_prev=duration_discounted_prev,
        )

    def get_list_critical_activities(self):
        """
        Translate the critical edges into critical activities.

        Returns
        -------
        critical_activities_list : list
            list of activity UUIDs (from column cp_activity_id in recorded_activities_df)
        """
        # get all edges on all critical paths
        if self.critical_edges_list is None:
            self.critical_edges_list = self.__find_critical_edges()

        # convert to activities and return
        list_activities = [
            self.simulation_graph.edges[edge]["cp_activity_id"]
            for edge in self.critical_edges_list
        ]
        return list_activities
