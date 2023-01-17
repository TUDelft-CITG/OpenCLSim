"""
module that contains class SimulationGraph (previously ActivityGraph)

Notes
-------
in original commit approx 400 lines
"""


class SimulationGraph:
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
    recorded_activity_df : recorded_activity_df
        attribute from instance of BaseCpLog
    dependency_list : list
        A key part of the recorded_activities_df is the ``cp_activity_id`` column. This column
        contains unique identifyers for simulated activities in time. This list
        is to contain tuples of those IDs defining dependencies between the
        corresponding activities. E.g. if the completion of activity with
        ``id==1`` triggers the start of activity with ``id==2``, then this
        should appear in the list as tuple ``(1, 2)``.
    """

    def __init__(
            self,
            recorded_activity_df,
            dependency_list):
        """ init """
        # set in self
        self.recorded_activity_df = self.__check_rec(recorded_activity_df)
        self.dependency_list = self.__check_dep(dependency_list)

        # init
        self.G = None

        # do the work
        self.__construct_graph()
        self.__find_critical_edges()

    def __check_rec(self, recorded_activity_df):
        """
        check validity of recorded_activity_df
        """
        # ..
        return recorded_activity_df

    def __check_dep(self, dependency_list):
        """
        check validity of dependency_list
        """
        # ..
        return dependency_list

    def __construct_graph(self):
        """
        set self.G, the netowrkx diGraph representing the OpenClSim simulation
        """
        pass

    def __find_critical_edges(self):
        """ iteratively run through self.G and find all critical edges"""
        pass

    def get_list_critical_activities(self):
        """
        translate the critical edges into critical activities

        Returns
        -------
        list of activity UUIDs (as found in column cp_activity_id from self.recorded_activity_df)
        """
        return []
