"""
Module contains DependenciesFromRecordedActivities that inherits from critical_path.base_cp.BaseCP
"""

from openclsim.critical_path.base_cp import BaseCP


class DependenciesFromRecordedActivities(BaseCP):
    """
    Build dependencies from recorded_activities_df.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_dependency_list(self):
        """
        Get dependencies directly from recorded activities (match on identical timestamps).

        This method determines dependencies between activities 'blindly' based
        on the simulation logs only. That is, purely based on timestamp and
        simulation object.

        The procedure of determining dependencies is as follows:

        1. Standard dependencies are those that have matching end and start
           times, and share at least one object.
        2. If a WAITING activity is logged, then it is assumed that the object
           is purposefully waiting for something. Hence, this should be
           included in the dependencies.

        Notes
        -----
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
            - Activities which are not recorded with/on a simulation object
              (e.g. weather plugin delays) are excluded.

        Returns
        -------
        dependency_list : list
            list of tuples like [(A1, A2), (A1, A3), (A3, A4)]
            where A2 depends on A1 (A1 'causes' A2) et cetera
        """
        if self.dependency_list is None:
            self.__set_dependency_list()

        return self.dependency_list

    def __set_dependency_list(self):
        """Hidden and protected method for the get_dependency_list."""
        # a recorded_activities_df is required - without the 'activity' (too many duplicates)
        recorded_activities_df = self.get_recorded_activity_df().copy()
        recorded_activities_df = recorded_activities_df.loc[
            recorded_activities_df.SimulationObject != "Activity", :
        ]
        dependency_list = []

        # loop over each unique cp_activity and find cp_activities which directly precede 'cp_act'
        for cp_act in recorded_activities_df.itertuples():
            dependencies = recorded_activities_df.loc[
                (recorded_activities_df.end_time == cp_act.start_time)
                & (recorded_activities_df.SimulationObject == cp_act.SimulationObject),
                :,
            ]

            if len(dependencies) > 0:
                if "WAITING" in dependencies.loc[:, "state"].tolist():
                    # if this cp_act is waiting for something,
                    # drop shared SimulationObject condition
                    dependencies = recorded_activities_df.loc[
                        recorded_activities_df.end_time == cp_act.start_time, :
                    ]
                depending_on = set(dependencies.cp_activity_id) - {
                    cp_act.cp_activity_id
                }
                for act_dep in depending_on:
                    dependency_list.append((act_dep, cp_act.cp_activity_id))

        self.dependency_list = list(set(dependency_list))
