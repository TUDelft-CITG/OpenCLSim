import datetime, time
import simpy

# package(s) for data handling
import pandas as pd
import numpy as np

import openclsim.core as core
import openclsim.model as model


class TestPluginClass(model.AbstractPluginClass):
    def __init__(
        self, *args, **kwargs,
    ):
        super().__init__(plugin_name="TestPlugin", *args, **kwargs)

    def pre_process(self, env, destination, engine_order, activity_log):
        print(f"plugin_data destination: {destination}")
        print(f"plugin_data engine_oder: {engine_order}")
        print(f"plugin_data activity_log: {activity_log}")
        activity_log.log_entry(
            "move activity pre-procesisng test plugin",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.UNKNOWN,
        )

    def post_process(
        self,
        env,
        destination,
        engine_order,
        activity_log,
        start_preprocessing,
        start_activity,
    ):
        print(f"plugin_data destination: {destination}")
        print(f"plugin_data engine_oder: {engine_order}")
        print(f"plugin_data activity_log: {activity_log}")
        print(f"plugin_data start_preprocessing: {start_preprocessing}")
        print(f"plugin_data start_activity: {start_activity}")
        activity_log.log_entry(
            "move activity post-procesisng test plugin",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.UNKNOWN,
        )


class HasTestPlugin:
    def __init__(
        self, *args, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if isinstance(self, model.PluginActivity):
            test_plugin = TestPluginClass()
            self.register_plugin(plugin=test_plugin, priority=2)
