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

    def __init__(self, dredge_criteria=None):
        assert isinstance(dredge_criteria, DredgeCriterion)
        self.dredge_criteria = dredge_criteria

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        if self.dredge_criteria is not None:
            return {}
        else:
            return {}

    def check_constraint(self):
        logger.info("Checking constraint in dredging plugin")
        return []

    def process_data(self, criterion) -> dict:
        result: dict = {}
        return result


class HasDredgePluginActivity(openclsim.model.PluginActivity):
    """Mixin for Activity to initialize DredgePluginActivity."""

    def __init__(self, dredge_criteria, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if dredge_criteria is not None and isinstance(
            self, openclsim.model.PluginActivity
        ):
            dredge_plugin = DredgePluginActivity(dredge_criteria=dredge_criteria)
            self.register_plugin(plugin=dredge_plugin, priority=2)
