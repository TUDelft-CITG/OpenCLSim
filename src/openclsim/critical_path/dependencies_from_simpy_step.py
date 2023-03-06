"""
module contains
- class DependenciesFromSimpy that inherits from critical_path.base_cp.BaseCP

TODO Later we need to add this or make new module
- class MyCustomSimpyEnv that inherits from simpy.env and patches env.step()
"""
import simpy
import pandas as pd
from functools import partial

from openclsim.critical_path.base_cp import BaseCP


class DependenciesFromSimpy(BaseCP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        df_step = pd.DataFrame(self.env.data_step,
                               columns=['t', 'e_id', 'type', 'value', 'prio', 'event_object'])
        df_cause_effect = pd.DataFrame(self.env.data_cause_effect,
                                       columns=['e_id_cause', 'e_id_effect'])

        return []


class MyCustomSimpyEnv(simpy.Environment):
    """TODO SCOPE 6"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_cause_effect = []
        self.data_step = []

    def step(self):
        """ we keep tack of some data"""

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

        self._monitor_cause_effect(eid, new_eids)
        self._monitor_step(timestamp, prio, eid, event)

    def _monitor_cause_effect(self, eid_current, eids_new=None):
        """add dependencies (triggers) to data """
        if eids_new is not None and len(eids_new) > 0:
            for new_eid in eids_new:
                self.data_cause_effect.append((eid_current, new_eid))

    def _monitor_step(self, t, prio, eid, event):
        self.data_step.append((t, eid, type(event), event.value, prio, event))
