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
        assert isinstance(
            self.env, MyCustomSimpyEnv
        ), "This module is not callable with the default simpy environment"

        print("TODO")
        self.step_logging_dataframe = pd.DataFrame(self.env.data_step,
                                                   columns=['t0', 't1', 'e_id', 'type', 'value',
                                                            'prio',
                                                            'event_object']).set_index('e_id')
        self.cause_effect_list = self.env.data_cause_effect

        # keep only those e_id tuples which mark dependencies between env.Timeouts
        all_dependencies = []
        remaining_eids = {tup[0] for tup in self.env.data_cause_effect}
        while len(remaining_eids) > 0:
            found_dependencies, seen_eids = self._loop_through(list(remaining_eids)[0])
            all_dependencies = all_dependencies + found_dependencies
            remaining_eids = remaining_eids - seen_eids

        # get recorded activities and convert times to floats (seconds since Jan 1970)
        recorded_activities_df = self.get_recorded_activity_df().copy()
        recorded_activities_df.start_time = \
            recorded_activities_df.start_time.astype('int64') / 10 ** 9
        recorded_activities_df.end_time = \
            recorded_activities_df.end_time.astype('int64') / 10 ** 9

        # rename the dependencies from dependencies with e_id to dependencies with cp_activity_id
        dependency_list = []
        for dependency in all_dependencies:
            cause = self._find_cp_act(dependency[0], recorded_activities_df)
            effect = self._find_cp_act(dependency[1], recorded_activities_df)
            dependency_list.append((cause, effect))

        return dependency_list

    def _loop_through(self, e_id_cause, prev_timeout=None, dependency_list=None, seen_eids=None,
                      all_tuples=None):
        """ helper function """

        # init when called for very first time
        if dependency_list is None:
            dependency_list = []
        if seen_eids is None:
            seen_eids = {e_id_cause}
        else:
            seen_eids.add(e_id_cause)
        if all_tuples is None:
            all_tuples = []

        # if e_id refers to Timeout event we keep this e_id as it may be the cause (or effect)
        # of another Timeout event
        if isinstance(self.step_logging_dataframe.loc[e_id_cause, 'event_object'],
                      simpy.events.Timeout):
            if prev_timeout is not None:
                dependency_list.append((prev_timeout, e_id_cause))
            prev_timeout = e_id_cause

        # see if effect and call recursive self again
        new_tuples = [tup for tup in self.cause_effect_list if tup[0] == e_id_cause]
        all_tuples = new_tuples + all_tuples

        if len(all_tuples) > 0:
            print(f"Passing eid {all_tuples[0][1]}")
            return self._loop_through(all_tuples[0][1],
                                      prev_timeout=prev_timeout,
                                      dependency_list=dependency_list,
                                      seen_eids=seen_eids, all_tuples=all_tuples[1:])
        else:
            # this id does not causes stuff done
            print(f"{e_id_cause} causes NO effect")
            return dependency_list, seen_eids

    def _find_cp_act(self, e_id, recorded_activities_df):
        """ get cp activity ID given a timewindow and an activity ID"""
        activity_id = self.step_logging_dataframe.loc[e_id, "event_object"].value
        start_time = self.step_logging_dataframe.loc[e_id, "t0"]
        end_time = self.step_logging_dataframe.loc[e_id, "t1"]
        matching_ids = recorded_activities_df.loc[
            ((recorded_activities_df.ActivityID == activity_id) &
             (recorded_activities_df.end_time == end_time)), "cp_activity_id"]
        if len(set(matching_ids)) == 1:
            cp_activity_id = matching_ids.iloc[0]
        else:
            raise UserWarning(f"No match found for {activity_id} at time {start_time}")
        return cp_activity_id


class MyCustomSimpyEnv(simpy.Environment):
    """TODO SCOPE 6"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_cause_effect = []
        self.data_step = []

    def step(self):
        """ we keep tack of some data"""
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
        """add dependencies (triggers) to data """
        if eids_new is not None and len(eids_new) > 0:
            for new_eid in eids_new:
                self.data_cause_effect.append((eid_current, new_eid))

    def _monitor_step(self, t0, t1, prio, eid, event):
        self.data_step.append((t0, t1, eid, type(event), event.value, prio, event))
