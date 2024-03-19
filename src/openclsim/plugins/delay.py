"""Weather plugin for the VO simulations."""

import openclsim.model as model


class HasDelayPlugin:
    """Mixin for Activity to initialize WeatherPluginActivity."""

    def __init__(self, delay_percentage=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if delay_percentage is not None and isinstance(self, model.PluginActivity):
            delay_plugin = DelayPlugin(delay_percentage=delay_percentage)
            self.register_plugin(plugin=delay_plugin, priority=3)


class DelayPlugin(model.AbstractPluginClass):
    """Mixin for all activities to add delay and downtime."""

    def __init__(self, delay_percentage=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.delay_factor = (
            delay_percentage / 100 if delay_percentage is not None else None
        )

    def post_process(
        self, env, activity_log, activity, start_activity, *args, **kwargs
    ):
        if self.delay_factor is None:
            return {}

        activity_delay = (env.now - start_activity) * self.delay_factor
        activity_label = {"type": "plugin", "ref": "delay"}

        return activity.delay_processing(
            env, activity_label, activity_log, activity_delay
        )
