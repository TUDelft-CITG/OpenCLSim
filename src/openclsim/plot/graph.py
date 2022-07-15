"""
Find the critical path through a sequance of activities and dependency links.

This module provides a graph-based solution for marking activities from an
OpenCLSim simulation. The critical path through a directed acyclic graph of
actitivies are defined by lying on a longest path.

Intended use is as follows:

.. code-block::

       analyser = ActivityGraph(super_log, list_dependencies)
       super_log_critical = analyser.mark_critical_paths()


"""
import copy
import datetime as dt
import logging
import time

import networkx as nx

# %%


class ActivityGraph:
    """
    Class to construct a ``networkx.DiGraph`` from simulation super-log.

    Create a graph from OpenCLSim activities in a log and dependencies and
    mark all activities/edges which are on a path of longest length. These are
    hence on the critical path.
    """

    # name of added columns to the super_log
    __COLNAME_CRITICAL = "is_critical"
    __COLNAME_GRAPH_EDGE = "graph_edge"

    # mapping from column name to attribute
    __SUPERLOG_COLUMNS = {
        "Activity": "activity",
        "SourceObject": "source_object",
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

    def __init__(self, super_log, list_dependencies):
        """Initiate the object."""
        # initiate by storing the inputs
        self.super_log = self.__check_log(super_log)
        self.list_dependencies = self.__check_dep(list_dependencies)

        # store a copy of log to work with
        self._critical_log = self.__prepare_log(super_log)

        # construct the graph based on the log and dependencies
        self.G = nx.DiGraph()
        self.__construct_graph()
        self.n_activities = len(
            [e for e in self.G.edges if self.G.edges[e]["edge_type"] == "activity"]
        )

        # get the duration of longest path
        self.max_duration = nx.dag_longest_path_length(self.G, weight="duration")

    def __check_log(self, super_log):
        """
        Check the ``super_log``.

        Standardize the super_log for further use renaming the columns and
        converting the duration column into seconds.
        """
        # check expected columns
        missing_columns = [
            c for c in self.__SUPERLOG_COLUMNS.keys() if c not in super_log.columns
        ]
        assert missing_columns == [], f"super_log is missing columns {missing_columns}"

        return super_log

    def __check_dep(self, list_dependencies):
        """
        Check the list_dependencies.

        Asserts that indeed a list is parsed that contains 2-tuples of
        cp-activities. The tuples are paired as
        ``(end cp-activity, start cp-activity)``, which will be prepended to
        comply with the nodes in the graph to be created.
        """
        assert isinstance(list_dependencies, list), "list_dependencies must be a list"

        list_dependencies = [
            (f"{self.__NODE_END_PREFIX} {end}", f"{self.__NODE_START_PREFIX} {start}")
            for end, start in list_dependencies
        ]

        return list_dependencies

    def __prepare_log(self, super_log):
        """
        Prepare the superlog to a workable format.

        TODO.
        """
        # rename columns to class defaults
        super_log = super_log.rename(columns=self.__SUPERLOG_COLUMNS)

        # make sure the duration is numeric
        super_log["duration"] = super_log["end_time"] - super_log["start_time"]
        if isinstance(super_log["duration"][0], dt.timedelta):
            super_log["duration"] = super_log["duration"].dt.total_seconds().astype(int)
        elif isinstance(super_log["duration"][0], (float, int)):
            pass
        else:
            raise Exception(
                f"Duration computed as type {type(super_log['duration'][0])} "
                "is not supported!"
            )

        # make sure all durations are positive
        assert all(
            super_log["duration"] >= 0
        ), "Negative durations encountered in activities."

        return super_log

    def __construct_graph(self):
        """
        Construct the graph.

        Construct the graph based on the activities in ``self._critical_log``
        and the list of dependencies in ``self.list_dependencies``. Alters
        ``self.G`` in place.
        """
        self.__create_activity_edges()
        self.__link_activity_edges()

        # check if the resulting graph is acyclic
        assert nx.is_directed_acyclic_graph(
            self.G
        ), "The resulting graph appears to be cyclic!"

    def __create_activity_edges(self):
        """
        Create nodes and edges for each individual activity.

        Converts all lines of ``self._critical_log`` into start and end nodes
        connected through an edge. All relevant attributes are added to these
        nodes and edges.
        """
        for ix, params in self._critical_log.iterrows():
            # names of the nodes by start/end of
            name_start = f"{self.__NODE_START_PREFIX} " f"{params['cp_activity_id']}"
            name_end = f"{self.__NODE_END_PREFIX} {params['cp_activity_id']}"

            # add the start node
            if name_start not in self.G.nodes:
                self.G.add_node(
                    name_start,
                    pos=(params["start_time"], ix),
                    time=params["start_time"],
                    cp_activity_id=params["cp_activity_id"],
                )

            # add the end node
            if name_end not in self.G.nodes:
                self.G.add_node(
                    name_end,
                    pos=(params["end_time"], ix),
                    time=params["end_time"],
                    cp_activity_id=params["cp_activity_id"],
                )

            # add an edge
            if (name_start, name_end) in self.G.edges:
                # edge is there, only add source object
                self.G.edges[(name_start, name_end)]["source_object"] += [
                    params["source_object"]
                ]
            else:
                # add the edge
                kwargs = {
                    "node_start": name_start,
                    "node_end": name_end,
                    "activity": params["activity"],
                    "source_object": [params["source_object"]],
                    "start_time": params["start_time"],
                    "state": params["state"],
                    "duration": params["duration"],
                    "end_time": params["end_time"],
                    "cp_activity_id": params["cp_activity_id"],
                    "edge_type": self.__EDGE_TYPES[0],
                    self.__COLNAME_CRITICAL: self.__CRITICAL[0],
                }
                self.G.add_edge(name_start, name_end, **kwargs)

    def __link_activity_edges(self):
        """
        Add connecting edges between linked activities.

        Uses the ``self.list_dependencies`` to link all loose nodes and edges
        together within the graph. Note that edges are added from the END of
        the first activity to the START of the second.
        """
        for name_start, name_end in self.list_dependencies:
            # extract some information on the times
            start_time = self.G.nodes[name_start]["time"]
            end_time = self.G.nodes[name_end]["time"]
            duration = end_time - start_time

            if isinstance(duration, dt.timedelta):
                duration = int(duration.total_seconds())
            elif isinstance(duration, (float, int)):
                pass
            else:
                raise Exception(
                    f"Duration computed as type {duration} " "is not supported!"
                )

            # add the edge from END to START
            kwargs = {
                "node_start": name_start,
                "node_end": name_end,
                "activity": None,
                "source_object": [None],
                "start_time": start_time,
                "state": None,
                "duration": duration,
                "end_time": end_time,
                "cp_activity_id": None,
                "edge_type": self.__EDGE_TYPES[1],
                self.__COLNAME_CRITICAL: self.__CRITICAL[0],
            }
            self.G.add_edge(name_start, name_end, **kwargs)

    def __get_list_critical_edges(
        self,
        discount_graph=None,
        list_critical=None,
        list_noncritical=None,
        to_discount=None,
        max_duration=None,
        t_max_end=None,
        duration_discounted_prev=None,
    ):
        """
        Create a list of edges on a longest path in the graph.

        This method recursively builds a list of edges in the activity graph
        which are on the longest path. In a nutshell the process is as follows:

        0. Create a shadow-copy of the activity graph.
        1. Find an initial longest path, mark all edges on it as such, and set
           their 'duration' to 10**-3 on a shadow-graph (i.e. discount all).
        2. Find a new longest path in the shadow-graph, and check if the
           duration in the original graph equals the maximum length. If so,
           good! Mark all edges as critical and set duration in the shadow
           graph to 10**-3. If not a feasible longest path, then mark the last
           edge as noncritical, and set its weight in the shadow graph to
           10**-6.
        3. Repeat until all edges are marked as critical or non-critical.
        """
        feasible_longest = False  # all edges on path can be discounted at once

        # the initial iteration
        if discount_graph is None:
            # make a copy of the graph to change weights
            discount_graph = copy.deepcopy(self.G)

            # get an initial longest path
            longest_path = nx.dag_longest_path(self.G, weight="duration")
            list_critical = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.G.edges[i]["edge_type"] == "activity"
            ]
            logging.debug(f"found initial longest path {list_critical}")

            # get the end time of the initial longest path
            t_max_end = self.G.nodes[longest_path[-1]]["time"]
            logging.debug(f"max duration {self.max_duration} and t_max end {t_max_end}")

            # ready to continue
            list_noncritical = []
            to_discount = []
            lp_duration = self.max_duration
            feasible_longest = True

        # any following iteration
        else:
            # get the current longest path in the discount graph
            longest_path = nx.dag_longest_path(discount_graph, weight="duration")
            lp_edges = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.G.edges[i]["edge_type"] == "activity"
            ]

            # get the original duration
            lp_duration = nx.path_weight(self.G, longest_path, weight="duration")
            t_end = self.G.nodes[longest_path[-1]]["time"]
            logging.debug(
                f"longest path found: duration {lp_duration} and t_end " f"{t_end}."
            )

            # see if this path is a feasible longest path in the original
            # i.e. must be max duration and same end time
            if lp_duration == self.max_duration and t_end == t_max_end:
                # create list of not-yet-marked-as-critical critical edges
                to_add_critical = [
                    edge for edge in lp_edges if edge not in list_critical
                ]
                if len(to_add_critical) > 0:
                    logging.debug(
                        "New elements on critical path path, "
                        f"adding {to_add_critical}"
                    )
                    list_critical += to_add_critical
                    feasible_longest = True
            else:
                to_add_discount = [edge for edge in lp_edges if edge not in to_discount]
                if len(to_add_discount) > 0:
                    logging.debug("adding to discount")
                    to_discount += to_add_discount

        # discount the edges, all at once, or only the last one
        if feasible_longest:
            logging.debug("discounting all")
            # in one go discount all activity edges in critical path
            list_edges = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.G.edges[i]["edge_type"] == "activity"
            ]
            for edge in list_edges:
                discount_graph.edges[edge]["duration"] = 10**-4
                self.G.edges[edge][self.__COLNAME_CRITICAL] = self.__CRITICAL[1]
            yet_to_discount = []
        else:
            yet_to_discount = [
                edge for edge in to_discount if edge not in list_noncritical
            ]
            if len(yet_to_discount) > 0:
                discount_graph.edges[yet_to_discount[-1]]["duration"] = 10**-8
                list_noncritical.append(yet_to_discount[-1])
                yet_to_discount = yet_to_discount[:-1]

        # iterate if we have yet to discount or if we have marked all edges
        if len(list_critical) + len(list_noncritical) == self.n_activities:
            return list_critical
        return self.__get_list_critical_edges(
            discount_graph=discount_graph,
            list_critical=list_critical,
            list_noncritical=list_noncritical,
            to_discount=yet_to_discount,
            max_duration=max_duration,
            t_max_end=t_max_end,
            duration_discounted_prev=duration_discounted_prev,
        )

    def mark_critical_activities(self):
        """
        Return the list of critical activities.

        First recursively mark all edges in the activity graph that are on a
        path of longest length. Then return a lost of all critical activities.
        """
        process_start = time.time()

        # get all edges on all critical paths
        edges_critical = self.__get_list_critical_edges()

        # convert to activities and return
        list_activities = [
            self.G.edges[edge]["cp_activity_id"] for edge in edges_critical
        ]
        print(f"-- total elapsed time {time.time() - process_start} seconds")

        return list_activities
