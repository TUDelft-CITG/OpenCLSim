"""
WIP module for graph-based dependency inspection from a list of top-level
activities.

TODO: docstrings for sure
"""
import itertools

import networkx as nx

from .. import model

# %%
DEPENDENCY_TYPES = {
    1: "ActivityDependency",
    2: "StartEventDependency",
    3: "ResourceDependency",
}

DEPENDENCY_TYPES_REVERSED = {v: k for k, v in DEPENDENCY_TYPES.items()}

# %% main function


class DependencyGraph:
    """
    WIP
    """

    def __init__(self, main_activities):
        """init"""
        # initiate
        self._main_activities = main_activities
        self.G = nx.DiGraph()

        # construct the graph
        self._constructGraph()

    def _constructGraph(self):
        """
        WIP construct the graph
        """
        # set up graph from initial base activities
        for activity in self._main_activities:
            add_act_node(activity, self.G)

        # replace non-basic nodes by drilling down
        nodesTODO = [x for x, y in self.G.nodes(data=True) if y["is_basic"] == False]
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
                x for x, y in self.G.nodes(data=True) if y["is_basic"] == False
            ]

    def getListDependencies(self):
        """Return the list of dependencies based on the graph"""
        return list(self.G.edges)

    def getListBaseActivities(self):
        """Return a list of the IDs of all base activities"""
        return list(self.G.nodes)


# %% aux functions
def is_basic_activity(activity):
    """
    WIP check if activity is base activity
    """
    if issubclass(type(activity), model.basic_activity.BasicActivity):
        return True
    elif issubclass(type(activity), model.move_activity.MoveActivity):
        return True
    elif issubclass(type(activity), model.shift_amount_activity.ShiftAmountActivity):
        return True
    else:
        return False


def get_activity_params(activity):
    """
    WIP return activity edge attributes
    """
    return {
        "activity": activity,
        "is_basic": is_basic_activity(activity),
    }


def add_act_node(activity, G):
    """
    WIP add an activity node to an existing graph
    """
    node_kwargs = get_activity_params(activity)
    name = node_kwargs["activity"].id
    G.add_node(name, **node_kwargs)


def add_dep_edge(G, src_node, dst_node, dep_type=None):
    """
    WIP add a dependency as directed edge
    """
    assert src_node in G.nodes, "src_node is not in G!"
    assert dst_node in G.nodes, "dst_node is not in G!"

    G.add_edge(*(src_node, dst_node), dependency_type=dep_type)


def _parallel_activity_subgraph(activity):
    """
    WIP create a graph from a single parallel activity
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
    WIP create a graph from a single while activity
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


# TODO: repeat == while


def _sequential_activity_subgraph(activity):
    """
    WIP create a graph from a single sequential activity
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
    WIP create a graph from a single activity
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
    WIP replace a single activity node in a main graph by a subgraph keeping
    the original connections in tact.
    """
    # all links into the node to be replaced, except the loop with itself should it exist
    existing_edges_in = list(main_G.in_edges(node))
    existing_nodes_in = [u for (u, v) in existing_edges_in if (u, v) != (node, node)]

    # all links out of the node to be replaced, except the loop with itself should it exist
    existing_edges_out = list(main_G.out_edges(node))
    existing_nodes_out = [v for (u, v) in existing_edges_out if (u, v) != (node, node)]

    # determine all new edges in and out
    new_edges_in = list(itertools.product(existing_nodes_in, start_nodes))
    new_edges_out = list(itertools.product(end_nodes, existing_nodes_out))

    # if the loop (node, node) existed, we must add all combinations (end, start) also
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
