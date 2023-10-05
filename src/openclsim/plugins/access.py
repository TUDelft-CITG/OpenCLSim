#!/usr/bin/env python3

"""Directory for the depth plugin."""

import numpy as np
import logging

import openclsim.model


logger = logging.getLogger(__name__)


class DredgeCriterion:
    """
    Used to add determine if a vessel can start it's dredging activity

    Parameters
    ----------
    ...

    """

    def __init__(
        self,
        name: str,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name


class DredgePluginActivity(openclsim.model.AbstractPluginClass):
    """Mixin for ShiftAmountActivity to initialize TestPluginShiftAmountActivity."""

    def __init__(self, dredge_criteria=None, destination=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(dredge_criteria, DredgeCriterion)
        self.dredge_criteria = dredge_criteria
        self.destination = destination

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        print("check dredging criteria", env.now)
       
        if self.dredge_criteria is not None:
            print("check if we need to dredge")
            if self.check_constraint():
                print("we are dredging")
                activity_label = {
                    "type": "plugin", "ref": "dredging"
                }
                waiting = 36000
                return self.delay_processing(env, activity_label, activity_log, waiting)
            return {}
        else:
            return {}

    def check_constraint(self):
        logger.info("True if we need to dredge")
        print(self.destination, self.destination.ABL, self.destination.DCL)
        if self.destination.ABL > self.destination.DCL:
            print("we are going to dredge")
            return True
        else:
            print("we are not dredging")
            return False

    def process_data(self, criterion) -> dict:
        result: dict = {}
        return result


class HasDredgePluginActivity(openclsim.model.PluginActivity):
    """Mixin for Activity to initialize DredgePluginActivity."""

    def __init__(self, dredge_criteria, destination, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if dredge_criteria is not None and isinstance(
            self, openclsim.model.PluginActivity
        ):
            dredge_plugin = DredgePluginActivity(dredge_criteria=dredge_criteria, destination=destination)
            self.register_plugin(plugin=dredge_plugin, priority=2)
