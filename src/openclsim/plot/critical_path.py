"""
This module provides tools to extract the critical path of activities from the
output of a simulation.
"""

# generic modules
import copy
import datetime as dt
import itertools
import logging
import time
import uuid

import networkx as nx
import pandas as pd

# internal modules
from .. import core, model
from ..model.shift_amount_activity import ShiftAmountActivity
from .log_dataframe import get_log_dataframe, get_subprocesses

# %% FIXED PARAMETERS
DEPENDENCY_TYPES = {
    1: "ActivityDependency",
    2: "StartEventDependency",
    3: "ResourceDependency",
}

DEPENDENCY_TYPES_REVERSED = {v: k for k, v in DEPENDENCY_TYPES.items()}


# %% MAIN CLASS DependencyGraph TO DETECT MODEL-BASED ACTIVITY DEPENDENCIES
class DependencyGraph:
    """
    Object used to capture top level dependencies in the model structure.

    This class can be used to generate a graph-based approach in detecting
    logical dependencies between OpenCLSim activities as extracted from the
    list of mail model activities. A directed graph is created where basic
    activities are represented by nodes, and their logical dependencies are
    the connecting directed graphs.

    For example, if a model setup contains a sequential activity
    ``A -> B -> C``, then the graph would show nodes ``A``, ``B`` and ``C`` for
    the activities, and the connecting edges ``(A, B)`` and ``(B, C)``.

    Parameters
    ----------
    main_activities : list
        The list of top level activities from the model setup. That is, if the
        model is set up with a WHILE activity on top level, then the list
        should only contain this WHILE activity, no matter the activities that
        are contained in it.
    """

    def __init__(self, main_activities):
        """Init."""
        # initiate
        self._main_activities = main_activities
        self.G = nx.DiGraph()

        # construct the graph
        self._constructGraph()

    def _constructGraph(self):
        """
        Construct the graph by drilling down from the top level activity all
        the way to the underlying base activities. Every time a node is created
        for an activity, and if it is not a basic activity, it is replaces by
        a sub-graph.

        For example, if we have a WHILE activity ``W``, containing a SEQUENTIAL
        activity ``S`` of the base activities ``A``, then ``B``, then ``C``,
        the graph would be built up in the following steps:

        1. Create single node ``W``, without edges.
        2. The ``W`` activity contains the sub-activity ``S``, hence replace
           node ``W`` by ``S``, and due to ``W`` being a while activity, add
           the edge ``(S, S)`` to the graph.
        3. Now, ``S`` contains the sequence ``A -> B -> C``, and must hence be
           replaced by the corresponding subgraph with nodes ``A``, ``B`` and
           ``C``, and the edges ``(A, B)`` and ``(B, C)``. By replacing ``S``,
           the resulting graph will have nodes ``A``, ``B`` and ``C``, edges
           ``(A, B)`` and ``(B, C)``, and also the edge ``(C, A)`` providing
           the recurrency from the while loop.
        4. Now all activities are base activities, hence this is the final
           form of the graph.

        """
        # set up graph from initial base activities
        for activity in self._main_activities:
            add_act_node(activity, self.G)

        # replace non-basic nodes by drilling down
        nodesTODO = [x for x, y in self.G.nodes(data=True) if y["is_basic"] is False]
        while nodesTODO != []:
            # select a node and activity
            cur_node = nodesTODO[0]
            cur_act = self.G.nodes[cur_node]["activity"]

            # replace with sub graph
            sub_G, start_nodes, end_nodes = activity_subgraph(cur_act)
            self.G = replace_node_with_subgraph(
                node=cur_node,
                main_G=self.G,
                sub_G=sub_G,
                start_nodes=start_nodes,
                end_nodes=end_nodes,
            )

            # finally re-evaluate the situation
            nodesTODO = [
                x for x, y in self.G.nodes(data=True) if y["is_basic"] is False
            ]

    def getListDependencies(self):
        """Return the list of dependencies based on the graph."""
        return list(self.G.edges)

    def getListBaseActivities(self):
        """Return a list of the IDs of all base activities."""
        return list(self.G.nodes)


# Aux functions


def get_activity_params(activity):
    """
    Returns a simple dictionary with the activity and the boolean indicating
    whether it is a basic activity.
    """
    return {
        "activity": activity,
        "is_basic": is_basic_activity(activity),
    }


def add_act_node(activity, G):
    """
    Adds an activity as node to a networkx graph G.
    """
    node_kwargs = get_activity_params(activity)
    name = node_kwargs["activity"].id
    G.add_node(name, **node_kwargs)


def add_dep_edge(G, src_node, dst_node, dep_type=None):
    """
    Adds a dependency between two activity nodes in a graph as a directed edge.
    """
    assert src_node in G.nodes, "src_node is not in G!"
    assert dst_node in G.nodes, "dst_node is not in G!"

    G.add_edge(*(src_node, dst_node), dependency_type=dep_type)


def _parallel_activity_subgraph(activity):
    """
    Generates a subgraph replacing a single parallel activity. The subgraph
    itself, and the start and end nodes are returned.
    """
    parent_id = activity.id
    sub_G = nx.DiGraph()

    start_nodes = []
    end_nodes = []

    for sub_act in activity.sub_processes:
        add_act_node(sub_act, sub_G)

        # add the parent
        sub_G.nodes[sub_act.id]["parent"] = parent_id

        # all are start end end nodes
        start_nodes.append(sub_act.id)
        end_nodes.append(sub_act.id)

        # note: no edges required!

    return sub_G, start_nodes, end_nodes


def _while_activity_subgraph(activity):
    """
    Generates a subgraph replacing a single while activity. The subgraph
    itself, and the start and end nodes are returned.
    """
    # OpenCLSim treats subprocesses in while activity as sequential
    sub_G, start_nodes, end_nodes = _sequential_activity_subgraph(activity)

    # simply need to add the loop from end to start
    # first get combinations of ends to starts
    end_to_start_combinations = list(itertools.product(end_nodes, start_nodes))

    # then add these edges
    for edge in end_to_start_combinations:
        add_dep_edge(sub_G, edge[0], edge[1], dep_type=DEPENDENCY_TYPES[1])

    return sub_G, start_nodes, end_nodes


def _sequential_activity_subgraph(activity):
    """
    Generates a subgraph replacing a single sequential activity. The subgraph
    itself, and the start and end nodes are returned.
    """
    parent_id = activity.id
    sub_G = nx.DiGraph()

    start_nodes = [activity.sub_processes[0].id]
    end_nodes = [activity.sub_processes[-1].id]
    all_nodes = []

    for sub_act in activity.sub_processes:
        add_act_node(sub_act, sub_G)

        # add the parent
        sub_G.nodes[sub_act.id]["parent"] = parent_id
        all_nodes.append(sub_act.id)

    # handle the edges
    edges = [uv for uv in zip(all_nodes[:-1], all_nodes[1:])]
    for edge in edges:
        add_dep_edge(sub_G, edge[0], edge[1], dep_type=DEPENDENCY_TYPES[1])

    return sub_G, start_nodes, end_nodes


def activity_subgraph(activity):
    """
    Generates a (sub)graph representation of a non-basic activity.
    """
    if issubclass(type(activity), model.parallel_activity.ParallelActivity):
        return _parallel_activity_subgraph(activity)
    elif issubclass(type(activity), model.while_activity.WhileActivity):
        return _while_activity_subgraph(activity)
    elif issubclass(type(activity), model.sequential_activity.SequentialActivity):
        return _sequential_activity_subgraph(activity)
    elif issubclass(type(activity), model.basic_activity.BasicActivity):
        sub_G = nx.DiGraph()
        add_act_node(activity, sub_G)
        node_name = activity.id
        return sub_G, [node_name], [node_name]
    else:
        raise TypeError(f"Activity type {type(activity)} not supported!")


def replace_node_with_subgraph(node, main_G, sub_G, start_nodes, end_nodes):
    """
    Replace a node-activity in a graph by a relevant sub-graph. The original
    connections are kept in tact.
    """
    # all links into the node to be replaced, except the loop with itself
    # should it exist
    existing_edges_in = list(main_G.in_edges(node))
    existing_nodes_in = [u for (u, v) in existing_edges_in if (u, v) != (node, node)]

    # all links out of the node to be replaced, except the loop with itself
    # should it exist
    existing_edges_out = list(main_G.out_edges(node))
    existing_nodes_out = [v for (u, v) in existing_edges_out if (u, v) != (node, node)]

    # determine all new edges in and out
    new_edges_in = list(itertools.product(existing_nodes_in, start_nodes))
    new_edges_out = list(itertools.product(end_nodes, existing_nodes_out))

    # if the loop (node, node) existed, we must add all combinations
    # (end, start) also
    if (node, node) in main_G.edges:
        loop_edges = list(itertools.product(end_nodes, start_nodes))
    else:
        loop_edges = []

    # compose the combined graph
    new_G = nx.compose(main_G, sub_G)

    # remove the node and all edges connected to it
    new_G.remove_node(node)  # KeyError if node does not exist
    new_G.remove_edges_from(existing_edges_in + existing_edges_out)

    # add last connecting edges
    new_G.add_edges_from(new_edges_in + new_edges_out + loop_edges)

    return new_G


# %% CLASS ActivityGraph FOR INSPECTING PATH OF LONGEST DURATION IN A DIGRAPH


class ActivityGraph:
    """
    Graph representation of simulated activities and their dependencies.

    Class to construct a ``networkx.DiGraph`` from simulation activity logs
    captured in a CpLog-object, and corresponding dependencies between those
    activities. Simulated activities appear in the graph as sets of _node-edge-
    node_, with a staet time, end time and a duration. Dependencies between
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
    cp_log : CpLog
        The CpLog object generated from the logs of all activities and object
        which are relevant for the critical path analysis.
    list_dependencies : list
        A key part of the cp_log is the ``cp_activity_id`` column. This column
        contains unique identifyers for simulated activities in time. This list
        is to contain tuples of those IDs defining dependencies between the
        corresponding activities. E.g. if the completion of activity with
        ``id==1`` triggers the start of activity with ``id==2``, then this
        should appear in the list as tuple ``(1, 2)``.
    """

    # name of added columns to the cp_log
    __COLNAME_CRITICAL = "is_critical"
    __COLNAME_GRAPH_EDGE = "graph_edge"

    # mapping from column name to attribute
    __SUPERLOG_COLUMNS = {
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

    def __init__(self, cp_log, list_dependencies):
        """Initiate the object."""
        # initiate by storing the inputs
        self.cp_log = self.__check_log(cp_log)
        self.list_dependencies = self.__check_dep(list_dependencies)

        # store a copy of log to work with
        self._critical_log = self.__prepare_log(cp_log)

        # construct the graph based on the log and dependencies
        self.G = nx.DiGraph()
        self.__construct_graph()
        self.n_activities = len(
            [e for e in self.G.edges if self.G.edges[e]["edge_type"] == "activity"]
        )

        # get the duration of longest path
        self.max_duration = nx.dag_longest_path_length(self.G, weight="duration")

    def __check_log(self, cp_log):
        """
        Check the correct format for the ``cp_log``.

        Standardize the cp_log for further use renaming the columns and
        converting the duration column into seconds.
        """
        # check expected columns
        missing_columns = [
            c for c in self.__SUPERLOG_COLUMNS.keys() if c not in cp_log.columns
        ]
        assert missing_columns == [], f"cp_log is missing columns {missing_columns}"

        return cp_log

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
            (
                f"{self.__NODE_END_PREFIX} {end}",
                f"{self.__NODE_START_PREFIX} {start}",
            )
            for end, start in list_dependencies
        ]

        return list_dependencies

    def __prepare_log(self, cp_log):
        """
        Prepare the cp_log to a workable format.

        Makes sure that column names are standardized, and that durations of
        activities are presented in seconds.
        """
        # rename columns to class defaults
        cp_log = cp_log.rename(columns=self.__SUPERLOG_COLUMNS)

        # make sure the duration is numeric
        cp_log["duration"] = cp_log["end_time"] - cp_log["start_time"]
        if isinstance(cp_log["duration"][0], dt.timedelta):
            logging.debug("Converting duration to seconds (float)")
            cp_log["duration"] = round(cp_log["duration"].dt.total_seconds(), 3)
        elif isinstance(cp_log["duration"][0], (float, int)):
            pass
        else:
            raise Exception(
                f"Duration computed as type {type(cp_log['duration'][0])} "
                "is not supported!"
            )

        # make sure all durations are positive
        assert all(
            cp_log["duration"] >= 0
        ), "Negative durations encountered in activities."

        return cp_log

    def __construct_graph(self):
        """
        Construct the graph.

        Construct the graph based of the activities in ``self._critical_log``
        and the list of dependencies in ``self.list_dependencies``. Alters
        underlying graph ``self.G`` in place.

        First, all activities are added as node-edge-node sets. Then connecting
        edges are added to link activities. A final check is performed to
        assert that the resulting graph is directed and acyclic.
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
        connected through an edge. All relevant attributes, such as the
        duration of an activity, are added to these nodes and edges.
        """
        for ix, params in self._critical_log.iterrows():
            # names of the nodes by start/end of
            name_start = f"{self.__NODE_START_PREFIX} " f"{params['cp_activity_id']}"
            name_end = f"{self.__NODE_END_PREFIX} " f"{params['cp_activity_id']}"

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

        Note: this method is to be called after
        ``self.__create_activity_edges()``.

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
            if duration > 0:
                logging.debug(f"dependency with duration {duration}")
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
           their 'duration' to 10**-3 on a shadow-graph (i.e. discount all
           edges which have already been marked).
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
            logging.debug(f"Found initial longest path {list_critical}.")

            # get the end time of the initial longest path
            t_start = self.G.nodes[longest_path[0]]["time"]
            t_max_end = self.G.nodes[longest_path[-1]]["time"]

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
            longest_path = nx.dag_longest_path(discount_graph, weight="duration")
            lp_edges = [
                i
                for i in zip(longest_path[:-1], longest_path[1:])
                if self.G.edges[i]["edge_type"] == "activity"
            ]

            # get the original duration
            lp_duration_discounted = nx.path_weight(
                discount_graph, longest_path, weight="duration"
            )
            lp_duration = round(
                nx.path_weight(self.G, longest_path, weight="duration"), 2
            )
            t_start = self.G.nodes[longest_path[0]]["time"]
            t_end = self.G.nodes[longest_path[-1]]["time"]
            logging.debug(
                f"longest path found: duration {lp_duration}, t_start "
                f"{t_start} and t_end {t_end}. (discounted duration "
                f"{lp_duration_discounted})"
            )

            # see if this path is a feasible longest path in the original
            # i.e. must be max duration and same end time
            if (lp_duration == round(self.max_duration, 2)) and (t_end == t_max_end):
                # create list of not-yet-marked-as-critical critical edges
                to_add_critical = [
                    edge for edge in lp_edges if edge not in list_critical
                ]
                if len(to_add_critical) > 0:
                    logging.debug(
                        "New elements on critical path path, "
                        f"adding {to_add_critical}."
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
                logging.debug(f"Discounting {yet_to_discount[-1]}")
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

        This method uses the underlying activity graph to mark all simulated
        actvities (i.e. edges in the graph) which are on a path of longest
        duration.

        The process of finding _a_ longest path in a directed non-cyclic graph
        is rather quick, however finding _all_ longest paths in such a graph
        was found out to be computationally expensive. Since we do not need to
        know all longest paths, but rather all activities that are on a longest
        path, the solution is found in a recursive function that marks edges
        in the graph as belonging to a longest path. This process has better
        computational performance.

        For more information, please check out class method
        ``self.__get_list_critical_edges()``.

        """
        logging.info("Start finding activities on the critical path.")
        process_start = time.time()

        # get all edges on all critical paths
        edges_critical = self.__get_list_critical_edges()

        # convert to activities and return
        list_activities = [
            self.G.edges[edge]["cp_activity_id"] for edge in edges_critical
        ]
        logging.info(f"-- total elapsed time {time.time() - process_start} seconds.")

        return list_activities


# %% MAIN CLASS CpLog FOR DETECTING THE CRITICAL PATH FROM A SIMULATION


class CpLog:
    """
    This class creates a CpLog (read as: 'critical path log') from the combined
    logbooks of (all) simulated objects and activities in an OpenCLSim
    simulation. Hence, the resulting logbooks from the HasLog mix-in.

    The class is initialized from a list of OpenCLSim simulation objects (e.g.
    vessels and sites) and a list of top level activities. Please ensure that
    the input contains all simulation objects and (top level) activities from
    your simulation which are relevant for extracting the critical path from
    the logs.

    The CpLog is to be called _after_ executing the OpenCLSim simulation.

    Parameters
    ---------------
    list_objects : list
        list of _all_ simulation objects (after simulation)
    list_activities : list
        list of _all_ top-node activity objects (after simulation)
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
        """Process off initialization a CpLog object."""
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

    def mark_critical_activities(self, dependencies):
        """
        Mark activities on the critical path.

        Use the ActivityGraph object to mark activities in the CpLog as
        belonging to a critical path.

        Parameters
        ----------
        dependencies : list of tuples, optional
            List of tuples of critical path ids of dependencies that were
            found.
        sparse : boolean, optional
            If True, a sparse dictionary is returned with activity id, the
            start and end time of the occurance, and a boolean indicating
            whether this activity is on the critical path. If False, a full
            DataFrame will be returned. The default is True.

        Returns
        -------
        log_out : list or DataFrame
            All activities with indication of being on critical path.
        """
        # initiate the ActivityGraph object
        my_graph = ActivityGraph(self.cp_log, dependencies)

        # get the list of critical activities
        list_actvities_critical = my_graph.mark_critical_activities()

        # mark them in the CpLog
        log_out = copy.deepcopy(self.cp_log)
        log_out.loc[:, "is_critical"] = log_out.loc[:, "cp_activity_id"].isin(
            list_actvities_critical
        )

        return log_out

    def get_dependencies_log_based(self):
        """
        Use the logbook of the simulated activities to determine dependency
        links between activities.

        This method determines dependencies between activities 'blindly' based
        on the simulation logs only. That is, purely based on timestamp and
        simulation object.

        The procedure of determining dependencies is as follows:

        1. Standard dependencies are those that have matching end and start
           times, and share at least one object.
        2. If a WAITING activity is logged, then it is assumed that the object
           is purposefully waiting for something. Hence, this should be
           included in the dependencies.

        .. warning::
            This method has a few known limitations which are listed below:
            - It is a rather grand assumption to conclude dependency from the
              log, i.e. matching time and location, only. As a result cases
              where 'being at the same place at the same time' may be wrongly
              interpreted as a dependency between activities.
            - It is assumed that there is always a common object for a
              dependency to occur. There are situations in which this may not
              be the case, for instance some level dependencies.
            - No explicit logic from the simulation model setup and objects can
              be extracted from the logbooks (after simulation)

        Returns
        ------------
        dependencies : list
            list of tuplese e.g. ``[(A, C), (B, C), (C, F)]`` when activity
            ``C`` depends on ``A`` and ``B`` and ``F`` on ``C``.

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

            # so standard dependencies requires identical time and (at least 1)
            # shared Source Object
            bool_dependencies = (
                bool_shared_source & bool_end_when_start & ~bool_this_activity
            )
            if sum(bool_dependencies) > 0:
                dependencies = self.cp_log.loc[bool_dependencies, :]
                if "WAITING" in dependencies.loc[:, "state"].tolist():
                    # This activity depends on waiting meaning: current
                    # activity might have been waiting on activity of other
                    # source object! We ASSUME that every activity of every
                    # source object with identical end time of this WAITING is
                    # a dependency for current activity
                    dependencies = self.cp_log.loc[
                        bool_end_when_start & ~bool_this_activity, :
                    ]

                # get all unique activities on which current cp_act depends
                activities_depending = dependencies.loc[:, "cp_activity_id"].unique()

                for act_dep in activities_depending:
                    list_dependencies.append((act_dep, cp_act))

        self.all_cp_dependencies = list_dependencies

        return self.all_cp_dependencies

    def get_dependencies_model_based(self):
        """
        Use the pre-defined model setup as well as the logbooks to determine
        dependency links between activities.

        This method uses the simulation objects, the activity hierarchy as well
        as the logged simulation to extract dependencies.

        The procedure of determining dependencies is as follows:

        1. Inspect the model setup of activities to extract logical
           dependencies between the conceptual activities. For instance, if the
           setup contains a WHILE activity, containing a SEQUENTIAL activity of
           sub activities ``A`` followed by ``B`` followed by ``C``, then we
           must find the logical dependencies ``(A, B)``, ``(B, C)`` and
           ``(C, A)``.
        2. Get activities based on start events.
        3. Get time related dependencies.
        4. Get resource limitation dependencies.
        5. Get wait dependencies.


        .. warning::
            The model based dependency detection is limited by the information
            in the current OpenCLSim logging. Known limitations are:
            - From the model setup the logical dependencies due to the activity
              definition and hierarchy can be extracted.
            - For resource limitations dependencies it is assumed that any
              activity at a ``HasResource`` object also requests a resource.
              The current logging does not explicity log the resource requests.
            - Start events are not explicitly logged, only level-based start
              events are supported as a preliminary function.
            - Waiting is ambiguous for detection of the critical path.

        """
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
            set(cp_dependencies + cp_depencies_res_limitation + cp_dependencies_wait)
        )

        return self.all_cp_dependencies

    def _make_critical_path_log(self, list_objects, list_activities):
        """
        Creates one single uniform log containing all activities from the
        logbooks of provided lists of object and activities. The format is
        such that any activity (in time) will get a single row in the log with
        a start and end time. A unique ID will also be added, i.e. unique in
        activity _and_ time.
        """
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


# %% AUXILIARY FUNCTIONS FOR THE CpLog CLASS


def get_dependencies_time(df_log_cp, dependencies_act):
    """
    Based on the model-based top level activity dependencies, e.g. resulting
    from the ``ActivityGraph``, check these dependencies as they appear in the
    logbook after simulation.

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
    # make unique - some duplicates are possible due to doubling of
    # simulation objects
    list_cp_dependencies = list(set(list_cp_dependencies))

    return list_cp_dependencies


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
    df_log : pd.DataFrame()
        format like return from combine_logs() or plot.get_log_dataframe()
        function definitions of OpenCLSim.

    Returns
    -------
    df_new : pd.DataFrame()
        The reformated and reshaped log.
    """
    # keep the df chronological
    df_log = df_log.sort_values(by=["Timestamp", "ActivityState"])
    df_log = df_log.reset_index()

    # make a list of indexes to handle
    to_handle = list(range(0, len(df_log)))

    # dummy for the output
    df_new = pd.DataFrame()

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
            & (df_log.loc[:, "SimulationObject"] == row_current.loc["SimulationObject"])
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
    Add a unique activity ID in time.

    OpenCLSim activities have their unique UUID. However, if the same activity
    is executed serveral times in through time, the same ID will appear in the
    log. For the analysis of the critical path of executed activities, it is
    desired to make the distinction between _activity A_ starting at time _t1_,
    and the same _activity A_ starting at time _t2_. This new ID is added as
    an additional column in the provided log as ``cp_activity_id``.

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
        df_new.loc[bool_match, "cp_activity_id"] = str(uuid.uuid4())

    return df_new


def combine_logs(objects, list_activities):
    """
    Combines the logs of given objects into a single dataframe.

    Parameters
    ------------
    objects : list
        a list of vessels, sites for which to plot all activities. These need
        to have had OpenCLSim logging!
    list_activities : list
         a list of top-activities of which also all sub-activities will be
         resolved, e.g.: the top-level while activity as ``[while_activity]``.
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
    Create single log of activities.

    Provided a list of OpenCLSim activities, this function creates a single
    log DataFrame with all activities combined.

    Parameters
    ------------
    activities : list
        A list of activities (after simulation). Note that these activities
        need to have OpenCLSim logging!
    """
    # check unique names
    names = [act.name for act in activities]
    assert len(names) == len(set(names)), "Names of your activities must be unique!"

    # concat
    log_all = pd.DataFrame()
    for act in activities:
        log = get_log_dataframe_activity(act)
        log["SimulationObject"] = "Activity"
        log_all = pd.concat([log_all, log])

    return log_all.sort_values("Timestamp").reset_index(drop=True)


# %% AUXILIARY FUNCTIONS FOR MODEL BASED DEPENDENCY DETECTION

# Definition of the base activities


def is_basic_activity(activity):
    """
    Auxiliary function to define an activity as a basic activity.

    An OpenCLSim activity is regarded as being a 'basic activity' if it is a
    ``BasicActivity``, ``MoveActivity`` or a ``ShiftAmountActivity``.

    Parameters
    ----------
    activity : OpenCLSim activity
        The activity to be inspected for being a basic activity.

    Returns
    -------
    bool
        Whether it has been found to be a basic activity.

    .. warning::
        This function is fixed only to OpenCLSim's activities
        ``BasicActivity``, ``MoveActivity`` and ``ShiftAmountActivity``. This
        function currently cannot cope with new additional activities that
        should be regarded as a basic activity too.

    """
    if issubclass(type(activity), model.basic_activity.BasicActivity):
        return True
    elif issubclass(type(activity), model.move_activity.MoveActivity):
        return True
    elif issubclass(type(activity), model.shift_amount_activity.ShiftAmountActivity):
        return True
    else:
        return False


# Resource capacity related dependencies


def get_resource_capacity_dependencies(cp_log, list_objects):
    """
    Given a ``CpLog`` instance, and a list of OpenCLSim model objects this
    function inspects dependencies between activities which seen to be due to
    resource limitations.

    For all objects it checks the number of resources that are available. Then
    in the log it keeps track of the number of activities that occur at this
    object, assuming that these activities request a resource from the object.
    Hence, assumptions can be made on how many resources have been in use at a
    particular moment in the simulation. As a result, resource limitation
    dependencies between activities can be registered.

    Parameters
    ------------
    cp_log : pd.DataFrame
        ``pd.DataFrame`` as within ``CpLog``
    list_objects : list
        list of all simulation objects (after simulation, e.g.
        [vessel, site, etc])

    .. warning::
        This function has some known limitations:
        - This function utilizes the logging and simulation objects after
          simulation. From this information it turns out that the actual
          resource request cannot be tracked down. Hence, it is assumed that
          if an activity takes place at an object, that also a resource is
          requested. This is not by default the case, examples can be created
          where an activity takes place at a simulation object without needing
          a resource request.
    """

    # step 1: get all objects for which a resource limitation is applicable
    objs_with_resource = [
        obj for obj in list_objects if check_resource(obj) is not None
    ]

    # init output
    list_dependencies_cp_all = []

    # step 2: see what is going on at one of the resource sites
    for obj_resource in objs_with_resource:
        nr_resources = check_resource(obj_resource)
        resource_log = get_timebased_overview_resource(cp_log, obj_resource.name)

        # now simply mark activies where utility > capacity and doublecheck
        # that at this (start) time others end
        bool_greater_than_cap = (resource_log.loc[:, "utility"] > nr_resources) & (
            resource_log.loc[:, "event"] == "START"
        )

        list_dependencies_cp = []
        for idx in bool_greater_than_cap.loc[bool_greater_than_cap].index.values:
            list_dependencies_cp = []
            # is this one really waiting, i.e. is there a gap  looking at
            # other simulation object (vessel)
            shared_simulation_objects = list(
                set(
                    cp_log.loc[
                        cp_log.loc[:, "cp_activity_id"]
                        == resource_log.loc[idx, "cp_activity_id"],
                        "SimulationObject",
                    ]
                )
                - {obj_resource.name}
            )
            if len(shared_simulation_objects) == 0:
                # no new dependencies to make, no shared simulation objects for
                # this activity: dependencies solely defined by activities
                continue
            else:
                for shared_simulation_object in shared_simulation_objects:
                    # so at this point we learn whether the shared object has
                    # a gap or not. If gap (no identical end times), then
                    # continue
                    bool_any_endings_now = (
                        cp_log.loc[:, "SimulationObject"] == shared_simulation_object
                    ) & (cp_log.loc[:, "end_time"] == resource_log.loc[idx, "datetime"])

                    # noinspection PyUnresolvedReferences
                    if sum(bool_any_endings_now) == 0:
                        # what is stopping now (so that this one can start)
                        bool_stopping_now = (resource_log.loc[:, "event"] == "STOP") & (
                            resource_log.loc[:, "datetime"]
                            == resource_log.loc[idx, "datetime"]
                        )
                        activities_stopping_now = resource_log.loc[
                            bool_stopping_now, "cp_activity_id"
                        ].tolist()
                        for act in activities_stopping_now:
                            list_dependencies_cp.append(
                                (act, resource_log.loc[idx, "cp_activity_id"])
                            )

                    # add the dependencies to the list
                    list_dependencies_cp_all = (
                        list_dependencies_cp_all + list_dependencies_cp
                    )

    # we may have found duplicates, return the unique connections
    return list(set(list_dependencies_cp_all))


# Check if an object had resource
def check_resource(obj):
    """
    Simple check if an object has resources.

    Parameters
    ----------
    obj : OpenCLSim simulation object
        The object to be inspected.

    Returns
    -------
    int, None
        If the object has resources, then the number of resources is returned.
        If not, then this function returns None.

    """
    if issubclass(type(obj), core.HasResource):
        return obj.resource.capacity
    else:
        return None


# Convenience function to keep track of resources


def get_timebased_overview_resource(df_log, name_simulation_object):
    """
    Get a DataFrame with all activities as START/STOP for a certain resource
    (simulation) object.

    Parameters
    ----------
    df_log : DataFrame
        The logging DataFrame.
    name_simulation_object : str
        The name of the simulation object.

    Returns
    -------
    resource_log : DataFrame
        DataFrame with the assumed resources taken at the simulation object.

    .. warning::
        From the current logging of activities the actual resource request
        cannot be derived. Hence, this function assumes that any activity at
        the object also uses a resource. Examples can be created where this is
        not the case, leading to mistakes. Fixes should be sought in updating
        the logging module.
    """
    bool_corresponding_to_object = df_log["SimulationObject"] == name_simulation_object

    # include WAIT as well
    activity_ids = df_log.loc[bool_corresponding_to_object, "ActivityID"].tolist()
    keep = (df_log.loc[:, "ActivityID"].isin(activity_ids)) & (
        df_log.loc[:, "SimulationObject"].isin([name_simulation_object, "Activity"])
    )
    resource_log_cp = df_log.loc[keep, :]

    # make a log of how many resources are used
    # START ==> take one resource
    # STOP ==> release one resource
    all_starts = pd.DataFrame(
        {
            "datetime": resource_log_cp["start_time"],
            "event": "START",
            "cp_activity_id": resource_log_cp["cp_activity_id"],
        }
    )
    all_stops = pd.DataFrame(
        {
            "datetime": resource_log_cp["end_time"],
            "event": "STOP",
            "cp_activity_id": resource_log_cp["cp_activity_id"],
        }
    )
    resource_log = pd.concat([all_starts, all_stops])

    # START always before stop (sedcondary ordering when same time)
    resource_log = resource_log.sort_values(["datetime", "event"]).reset_index(
        drop=True
    )

    # first add resource utility level
    resource_log.loc[:, "utility"] = None
    ut_current = 0
    for idx, row in resource_log.iterrows():
        if row.loc["event"] == "START":
            ut_current += 1
        if row.loc["event"] == "STOP":
            ut_current -= 1
        resource_log.loc[idx, "utility"] = ut_current
    return resource_log


# Detect start-event triggered activities
def get_start_events(acts):
    """
    This function gets all base activities with a single start event
    condition.

    Parameters
    ------------
    acts : list
        Main activity or list of main activities (after simulation).

    Returns
    ----------
    list_start_dependencies : list
        list of start_event dictionairies, enriched with activity id which has
        this start event as attribute.
    """
    list_all_base_activities = [
        a for a in get_subprocesses(acts) if is_basic_activity(a)
    ]

    list_start_dependencies = []
    for ba in list_all_base_activities:
        if ba.start_event is not None and len(ba.start_event) == 1:
            dict_start_event = ba.start_event[0]
            dict_start_event["activity_id"] = ba.id
            list_start_dependencies.append(dict_start_event)

    return list_start_dependencies


# Get dependencies based on start events
def get_act_dependencies_start(acts):
    """
    Get activity dependencies based on start event conditions.
    For now only 'container' type supported for base activities.

    Parameters
    ------------
    acts : list
        main activity or list of main activities (after simulation)

    Returns
    ----------
    list_act_dependencies_start : list
        list of dependencies (tuples with activity ids)

    .. warning::
        Start events are currently only detected based on level-related start
        events. Hence, this function does not capture all start events!

    """
    list_start_dependencies = get_start_events(acts)

    # now see which base activities deal with container level
    list_all_base_activities = [
        a for a in get_subprocesses(acts) if is_basic_activity(a)
    ]
    list_act_dependencies_start = []
    for start_dependency in list_start_dependencies:
        if start_dependency["type"] == "container":
            # dependency on all ShiftAmount Activities with destination as in
            # start_dependency
            dependent_on = [
                a
                for a in list_all_base_activities
                if issubclass(type(a), ShiftAmountActivity)
                and a.destination == start_dependency["concept"]
            ]
            for dep in dependent_on:
                list_act_dependencies_start.append(
                    (dep.id, start_dependency["activity_id"])
                )
        else:
            logging.warning(
                f"Finding dependencies for start condition type"
                f" {start_dependency['type']} not (yet) supported"
            )
    return list_act_dependencies_start


# Waiting related start events
def get_wait_dependencies_cp(df_log_cp):
    """
    Get/assume dependencies between activities related to waiting. Waiting
    activities must explicitly be marked in the CpLog object as ``WAITING``.

    Parameters
    -----------
    df_log_cp : pd.DataFrame
        the dataframe within object of class CpLog

    Returns
    --------
    list_wait_dependencies : list
        a list of dependencies (tuples with cp_Aativity_id values)

    .. warning::
        The definition of ``WAITING`` is up for discussion, as well as when and
        whether waiting is part of the critical path in the first place.

    .. warning::
        This function is preliminary, and hence has its limitations. Mostly due
        to critical information for dependencies in the way OpenCLSim now logs
        its information. For proper dependency checks for extracting the
        critical path, the logging module of OpenCLSim must be extended.

    """
    list_wait_dependencies = []
    bool_is_wait = df_log_cp.loc[:, "state"] == "WAITING"
    if bool_is_wait.any():
        for idx, row in df_log_cp.loc[bool_is_wait, :].iterrows():
            list_ids_before = df_log_cp.loc[
                (df_log_cp.loc[:, "ActivityID"] == row.loc["ActivityID"])
                & (df_log_cp.loc[:, "end_time"] == row.loc["start_time"]),
                "cp_activity_id",
            ].tolist()
            list_ids_after = df_log_cp.loc[
                (df_log_cp.loc[:, "ActivityID"] == row.loc["ActivityID"])
                & (df_log_cp.loc[:, "start_time"] == row.loc["end_time"]),
                "cp_activity_id",
            ].tolist()

            # by default only 1 activity with same activity ID before/after
            # wait, so no explicit check - grab element 0
            if len(list_ids_before) > 0:
                list_wait_dependencies.append(
                    (list_ids_before[0], row.loc["cp_activity_id"])
                )
            if len(list_ids_after) > 0:
                list_wait_dependencies.append(
                    (row.loc["cp_activity_id"], list_ids_after[0])
                )
    else:
        logging.info("No waiting activity in this critical path log")

    return list_wait_dependencies


# %%
def get_log_dataframe_activity(activity, keep_only_base=True):
    """
    Get the log of the activity object in a pandas dataframe.

    Parameters
    ----------
    activity : object
        object from which the log is returned as a dataframe sorted by
        "Timestamp"
    keep_only_base : boolean
        if True (default) only the base (containing no sub_processes)
        activities are kept in pd.DataFrame output
    """

    list_all_activities = get_subprocesses(activity)
    id_map = {act.id: act.name for act in list_all_activities}

    df_all = pd.DataFrame()
    for sub_activity in list_all_activities:

        df = (
            pd.DataFrame(sub_activity.log)
            .sort_values(by=["Timestamp"])
            .sort_values(by=["Timestamp"])
        )

        df_concat = pd.concat(
            [
                df.filter(items=["ActivityID"]),
                pd.DataFrame(sub_activity.log).filter(["Timestamp", "ActivityState"]),
                pd.DataFrame(sub_activity.log["ObjectState"]),
            ],
            axis=1,
        )

        df_all = pd.concat([df_all, df_concat], axis=0)
        df_all.loc[:, "Activity"] = df_all.loc[:, "ActivityID"].replace(id_map)

    if keep_only_base:
        # filter out all non-base activities
        my_graph = DependencyGraph([activity])
        df_all = df_all.loc[
            df_all.loc[:, "ActivityID"].isin(my_graph.getListBaseActivities()),
            :,
        ]

    return df_all
