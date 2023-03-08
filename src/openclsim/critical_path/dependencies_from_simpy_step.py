"""
this module contains two classes which are both required if critical path (dependencies)
are to be found with method 'simpy step':
- class DependenciesFromSimpy that inherits from critical_path.base_cp.BaseCP and has specific
 get_dependency_list method (as is the case with the other methods as well)
- class MyCustomSimpyEnv that inherits from simpy.env and patches env.step()
"""
import simpy
import pandas as pd
import copy

from openclsim.critical_path.base_cp import BaseCP


class DependenciesFromSimpy(BaseCP):
    """
    Build dependecies from recorded_activities_df
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # other attributes, specific for this (child) class
        self.step_logging_dataframe = None
        self.cause_effect_list = None

    def get_dependency_list(self):
        """
        Get dependencies from simpy logging by analysing
        the data as saved with the patched env.step function

        requires self.env (instance MyCustomSimpy)

        Returns
        -------
        dependency_list : list
            list of tuples like [(A1, A2), (A1, A3), (A3, A4)]
            where A2 depends on A1 (A1 'causes' A2) et cetera
        """
        self.get_recorded_activity_df()

        if self.dependency_list is None:
            self.__set_dependency_list()

        return self.dependency_list

    def __set_dependency_list(self):
        """
        Hidden and protected method for the get_dependency_list.

        This method recursively walks through the simpy dependencies
        (as the 'monkeypatched' step function records these) and keeps only those depencencies
        which are a timeout event. Then we translate the IDs of these dependencies from
        the original simpy e_id values to our openclsim cp_activity_id values.
        """
        assert isinstance(
            self.env, MyCustomSimpyEnv
        ), "This module is not callable with the default simpy environment"

        self.step_logging_dataframe = pd.DataFrame(self.env.data_step,
                                                   columns=['t0', 't1', 'e_id', 'type', 'value',
                                                            'prio',
                                                            'event_object']).set_index('e_id')
        self.cause_effect_list = self.env.data_cause_effect

        # Define some globals to which the recursive functions/while loop can append
        DEPENDENCIES_SIMPY = []
        SEEN = []

        def __loop_through(tree_input, elem=None, last_seen=None):
            """
            Hidden and protected method for __set_dependency_list2.

            This function will walk through a hierarchical tree which is represented by
            list of tuples.
            Each tuple is a dependency and contains a cause (first element tuple) and
            effect (second and last element tuple).
            """
            if elem is None:
                elem = tree_input[0][0]

            # note that we have seen this one
            SEEN.append(elem)

            # get effects
            effects_this_elem = [tup[1] for tup in tree_input if tup[0] == elem]
            relevant_timeout = \
                isinstance(self.step_logging_dataframe.loc[elem, 'event_object'],
                           simpy.events.Timeout) and \
                self.step_logging_dataframe.loc[elem, 'event_object']._delay > 0

            if relevant_timeout:
                # relevant to SAVE
                if last_seen is not None:
                    DEPENDENCIES_SIMPY.append((last_seen, elem))
                last_seen = elem

            for effect_this_elem in effects_this_elem:
                __loop_through(tree_input, elem=effect_this_elem, last_seen=last_seen)

            return None

        # get all relevant dependencies from the simpy depencies,
        # that is find how the timeouts depend on one another.
        tree = copy.deepcopy(self.cause_effect_list)
        while len(tree) > 0:
            __loop_through(tree)
            tree = [tup for tup in tree if tup[0] not in SEEN]

        # get recorded activities and convert times to floats (seconds since Jan 1970)
        recorded_activities_df = self.recorded_activities_df.copy()
        recorded_activities_df.start_time = \
            round(recorded_activities_df.start_time.astype('int64') / 10 ** 9, 4)
        recorded_activities_df.end_time = \
            round(recorded_activities_df.end_time.astype('int64') / 10 ** 9, 4)

        # rename the dependencies from dependencies with e_id to dependencies with cp_activity_id
        dependency_list = []
        for dependency in DEPENDENCIES_SIMPY:
            cause = self._find_cp_act(dependency[0], recorded_activities_df)
            effect = self._find_cp_act(dependency[1], recorded_activities_df)
            dependency_list.append((cause, effect))
        self.dependency_list = dependency_list
        print("Dependency list made")

    def _find_cp_act(self, e_id, recorded_activities_df):
        """
        Get cp activity ID given a timewindow and an activity ID.

        Parameters
        ----------
        e_id : int
            execution id from simpy
        recorded_activities_df : pd.DataFrame
            from self.get_recorded_activity_df()
        """
        activity_id = self.step_logging_dataframe.loc[e_id, "event_object"].value
        end_time = round(self.step_logging_dataframe.loc[e_id, "t1"], 4)
        matching_ids = recorded_activities_df.loc[
            ((recorded_activities_df.ActivityID == activity_id) &
             (recorded_activities_df.end_time == end_time)), "cp_activity_id"]
        if len(set(matching_ids)) == 1:
            cp_activity_id = matching_ids.iloc[0]
        else:
            raise UserWarning(f"No match found for {activity_id} at (end)time {end_time}")
        return cp_activity_id


class MyCustomSimpyEnv(simpy.Environment):
    """
    Class is child of simpy.Environment and passes on all arguments on initalization.
    The 'step' method is overwritten (or 'monkeypatched') in order to log some data of
    simulation into self.data_step and self.data_cause_effect. The former saves some metadata
    of the Event such as e_id (execution ID), simulation time, prio and event type (list of tuples).
    The latter saves which e_id scheduled another e_id and is hence a list of cause-effect tuples.
    """

    def __init__(self, *args, **kwargs):
        """ Initialization. """
        super().__init__(*args, **kwargs)
        self.data_cause_effect = []
        self.data_step = []

    def step(self):
        """
        The 'step' method is overwritten (or 'monkeypatched') in order to log some data of
        simulation into self.data_step and self.data_cause_effect.
        """
        time_start = copy.deepcopy(self.now)
        if len(self._queue):
            timestamp, prio, eid, event = self._queue[0]
            old_eids = set([t[2] for t in self._queue])
        else:
            timestamp, prio, eid, event = None, None, None, None
            old_eids = {}

        super().step()

        if len(self._queue):
            new_eids = list(set([t[2] for t in self._queue]) - old_eids)
        else:
            new_eids = []

        time_end = copy.deepcopy(self.now)

        self._monitor_cause_effect(eid, new_eids)
        self._monitor_step(time_start, time_end, prio, eid, event)

    def _monitor_cause_effect(self, eid_current, eids_new=None):
        """
        Append dependencies (triggers) to data_cause_effect.
        """
        if eids_new is not None and len(eids_new) > 0:
            for new_eid in eids_new:
                self.data_cause_effect.append((eid_current, new_eid))

    def _monitor_step(self, t0, t1, prio, eid, event):
        """
        Append metadata concerning events data_step.
        """
        self.data_step.append((t0, t1, eid, type(event), event.value, prio, event))
