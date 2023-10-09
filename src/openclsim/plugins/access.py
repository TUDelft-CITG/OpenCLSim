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
            print("wait until we need to dredge again")
            activity_label = {"type": "plugin", "ref": "dredging"}
            waiting = self.time_until_dredging_needed()
            print(f"waiting for {waiting} seconds")
            return activity.delay_processing(env, activity_label, activity_log, waiting)
        else:
            return {}

    def should_dredge(self):
        logger.info("True if we need to dredge")
        print(self.destination, self.destination.ABL, self.destination.DCL)
        if self.destination.ABL > self.destination.DCL:
            print("we are going to dredge")
            return True
        else:
            print("we are not dredging")
            return False

    def time_until_dredging_needed(self):
        """compute how long until next dredging cycle starts"""
        remaining_bed_level = self.destination.DCL - self.destination.ABL
        print(f"remaining_bed_level: {remaining_bed_level}")
        if remaining_bed_level < 0:
            return 0

        # m / m/s
        remaining_duration = remaining_bed_level / self.destination.SR
        return remaining_duration

    def process_data(self, criterion) -> dict:
        result: dict = {}
        return result


class HasDredgePluginActivity(openclsim.model.PluginActivity):
    """Mixin for Activity to initialize DredgePluginActivity."""

    def __init__(self, dredge_criteria, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assert hasattr(self, "destination"), f"{self} should have a destination"
        destination = self.destination
        if dredge_criteria is not None and isinstance(
            self, openclsim.model.PluginActivity
        ):
            dredge_plugin = DredgePluginActivity(
                dredge_criteria=dredge_criteria, destination=destination
            )
            self.register_plugin(plugin=dredge_plugin, priority=2)
