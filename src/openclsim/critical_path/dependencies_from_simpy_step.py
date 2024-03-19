"""
This module contains two classes which are both required if critical path (dependencies)
are to be found with method 'simpy step':
- class DependenciesFromSimpy that inherits from critical_path.base_cp.BaseCP and has specific
 get_dependency_list method (as is the case with the other methods as well)
- class CriticalPathEnvironment that inherits from simpy.Environment and 'patches' env.step()
"""

import copy
import logging

import pandas as pd
import simpy

from openclsim.critical_path.base_cp import BaseCP


class DependenciesFromSimpy(BaseCP):
    """
    Build dependencies from data as recorded with CriticalPathEnvironment instance.
    """

    def __init__(self, *args, **kwargs):
        """Initialization."""
        super().__init__(*args, **kwargs)
        if not isinstance(self.env, CriticalPathEnvironment):
            raise TypeError(
                "DependenciesFromSimpy needs to be initialized"
                " with a CriticalPathEnvironment"
            )

        # other attributes, specific for this (child) class
        self.step_logging_dataframe = pd.DataFrame(
            self.env.data_step,
            columns=["t0", "t1", "e_id", "type", "value", "prio", "event_object"],
        ).set_index("e_id")
        self.__cause_effect_list = copy.deepcopy(self.env.data_cause_effect)

    def get_dependency_list(self):
        """
        Get dependencies from simpy logging by analysing
        the data as saved within the AlteredStepEnv instance.

        Returns
        -------
        dependency_list : list
            Dependency_list contains tuples like [(A1, A2), (A1, A3), (A3, A4)]
            where A2 depends on A1 (A1 'causes' A2) etcetera.
        """
        self.get_recorded_activity_df()

        if self.dependency_list is None:
            self.__set_dependency_list()

        return self.dependency_list

    def __set_dependency_list(self):
        """
        Hidden and protected method for the get_dependency_list.

        This method recursively walks through the simpy dependencies
        (as the 'monkey-patched' step function recorded these) and keeps only those dependencies
        which are a timeout event. Then we translate the IDs of these dependencies from
        the original simpy e_id values to our openclsim cp_activity_id values.
        """
        # Define some globals to which the recursive functions/while loop can append
        DEPENDENCIES_OPENCLSIM = []
        SEEN = []

        def __extract_openclsim_dependencies(tree_input, elem=None, last_seen=None):
            """
            Extract the relevant (OpenCLSim) dependencies from the complete list
            of all Simpy dependencies.

            This function will walk through a dependency tree which is represented by
            list of tuples (e.g. [(1, 2), (2, 3), (2, 4))]). Each tuple contains two
            eids (event-IDs) and can be seen a dependency with a cause (first element
            tuple) and effect (second and last element tuple).
            CriticalPathEnvironment registers all events, but we are only
            interested in events which are OpenClSim activities with duration,
            i.e. we are only interested in Timeout event with a _delay attribute > 0.
            This function extracts such dependencies (which Timeout causes which timeout)
            from the original tree_input.
            """
            if elem is None:
                elem = tree_input[0][0]

            # note that we have seen this one
            SEEN.append(elem)

            # get effects
            effects_this_elem = [tup[1] for tup in tree_input if tup[0] == elem]
            # we only want dependencies that are 1) a Timeout and 2) have a delay > 0
            # (because these events take time)
            relevant_timeout = (
                isinstance(
                    self.step_logging_dataframe.loc[elem, "event_object"],
                    simpy.events.Timeout,
                )
                and self.step_logging_dataframe.loc[elem, "event_object"]._delay > 0
            )

            if relevant_timeout:
                # relevant to SAVE
                if last_seen is not None:
                    DEPENDENCIES_OPENCLSIM.append((last_seen, elem))
                last_seen = elem

            for effect_this_elem in effects_this_elem:
                logging.debug(f"Effect {effect_this_elem} from {effects_this_elem}")
                __extract_openclsim_dependencies(
                    tree_input, elem=effect_this_elem, last_seen=last_seen
                )

            return None

        # get all relevant dependencies from the simpy dependencies,
        # that is find how the timeouts depend on one another.
        tree = copy.deepcopy(self.__cause_effect_list)
        while len(tree) > 0:
            __extract_openclsim_dependencies(tree)
            tree = [tup for tup in tree if tup[0] not in SEEN]

        # get recorded activities and convert times to floats (seconds since Jan 1970)
        recorded_activities_df = self.recorded_activities_df.copy()
        recorded_activities_df.start_time = round(
            recorded_activities_df.start_time.astype("int64") / 10**9, 4
        )
        recorded_activities_df.end_time = round(
            recorded_activities_df.end_time.astype("int64") / 10**9, 4
        )

        # rename the dependencies from dependencies with e_id to dependencies with cp_activity_id
        self.dependency_list = [
            (
                self._find_cp_act(dependency[0], recorded_activities_df),
                self._find_cp_act(dependency[1], recorded_activities_df),
            )
            for dependency in DEPENDENCIES_OPENCLSIM
        ]

    def _find_cp_act(self, e_id, recorded_activities_df):
        """
        Get cp activity ID given a time-window and an activity ID.

        Parameters
        ----------
        e_id : int
            Execution id from simpy.
        recorded_activities_df : pd.DataFrame
            From self.get_recorded_activity_df().
        """
        activity_id = self.step_logging_dataframe.loc[e_id, "event_object"].value
        end_time = round(self.step_logging_dataframe.loc[e_id, "t1"], 4)
        matching_ids = recorded_activities_df.loc[
            (
                (recorded_activities_df.ActivityID == activity_id)
                & (recorded_activities_df.end_time == end_time)
            ),
            "cp_activity_id",
        ]
        if len(set(matching_ids)) == 1:
            cp_activity_id = matching_ids.iloc[0]
        else:
            raise ValueError(
                f"No recorded activity found for"
                f" activityID {activity_id} at (end)time {end_time}"
                f" . Make sure to add `value=activity_id` to timeout events you yield."
            )
        return cp_activity_id


class CriticalPathEnvironment(simpy.Environment):
    """
    Class is child of simpy.Environment and passes on all arguments on initialization.
    The 'step' method is overwritten (or 'monkey-patched') in order to log some data of
    simulation into self.data_step and self.data_cause_effect. The former saves some metadata
    of the Event such as e_id (execution ID), simulation time, prio and event type (list of tuples).
    The latter saves which e_id scheduled another e_id and is hence a list of cause-effect tuples.
    """

    def __init__(self, *args, **kwargs):
        """Initialization."""
        super().__init__(*args, **kwargs)
        self.data_cause_effect = []
        self.data_step = []

    def step(self):
        """
        The 'step' method is overwritten (or 'monkey-patched') in order to log some data of
        simulation into self.data_step and self.data_cause_effect. Before and after
        the original step function we look at the self._queue and deduce dependencies.
        """
        t_before = copy.deepcopy(self.now)
        if len(self._queue):
            _, prio, e_id, event = self._queue[0]
            e_ids_before = set([t[2] for t in self._queue])
        else:
            _, prio, e_id, event = None, None, None, None
            e_ids_before = {}

        super().step()

        if len(self._queue):
            e_ids_new = list(set([t[2] for t in self._queue]) - e_ids_before)
        else:
            e_ids_new = []

        t_after = copy.deepcopy(self.now)

        self._monitor_cause_effect(e_id, e_ids_new)
        self._monitor_step(t_before, t_after, prio, e_id, event)

    def _monitor_cause_effect(self, e_id_current, e_ids_new):
        """
        Append dependencies (triggers) to data_cause_effect.

        Parameters
        ----------
        e_id_current : int
            Simpy execution ID (cause).
        e_ids_new : list
            Simpy execution IDs (effect).
            If empty list, eid_current does not trigger another event.
        """
        if len(e_ids_new) > 0:
            for new_eid in e_ids_new:
                self.data_cause_effect.append((e_id_current, new_eid))

    def _monitor_step(self, t0, t1, prio, e_id, event):
        """
        Append metadata from events to data_step.

        Parameters
        ----------
        t0 : float
            Numeric timestamp before execution of step() method.
        t1 : float
            Numeric timestamp before execution of step() method.
            This t1 corresponds with actual time when event has ended in simulation time,
            whereas t0 might be 'off' (due to other events that need to be handled in simulation).
        prio : int
            Priority attribute of event.
        e_id : int
            Simpy execution ID which is handled (whose callbacks/triggers are handled)
            in step() method.
        event : instance of (Simpy) Event
            Event (with eid) which is handled.
        """
        self.data_step.append((t0, t1, e_id, type(event), event.value, prio, event))
