"""Weather plugin for calculating weather delay."""
import datetime
import pandas as pd
import numpy as np

import openclsim.core as core
import openclsim.model as model
import math


class WorkabilityCriterion:
    """WorkabilityCriterion class

    Used to add limits to vessels (and therefore acitivities)
    event_name: name of the event for which this criterion applies
    condition: column name of the metocean data (Hs, Tp, etc.)
    minimum: minimum value
    maximum: maximum value
    window_length: minimal length of the window (minutes)"""

    def __init__(
        self,
        event_name,
        condition,
        minimum=math.inf * -1,
        maximum=math.inf,
        window_length=datetime.timedelta(minutes=60),
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.event_name = event_name
        self.condition = condition
        self.minimum = minimum
        self.maximum = maximum
        self.window_length = window_length


class WorkabilityCriteriaMixin:
    """Activity mixin to enable the plugin."""

    def calc_work_restrictions(self, location):
        for criterion in self.metocean_criteria:
            condition = self.metocean_data[criterion.condition]
            ix_condition = condition <= criterion.maximum
            ix_starts = ~ix_condition.values[:-1] & ix_condition.values[1:]
            ix_ends = ix_condition.values[:-1] & ~ix_condition.values[1:]
            if ix_condition[0]:
                ix_starts[0] = True
            if ix_starts.sum() > ix_ends.sum():
                ix_ends[-1] = True
            t_starts = condition.index[:-1][ix_starts]
            t_ends = condition.index[:-1][ix_ends]
            dt_windows = t_ends - t_starts
            ix_windows = dt_windows >= criterion.window_length
            ranges = np.concatenate(
                (
                    t_starts[ix_windows].values.reshape((-1, 1)),
                    (t_ends[ix_windows] - criterion.window_length).values.reshape(
                        (-1, 1)
                    ),
                ),
                axis=1,
            )
            self.work_restrictions.setdefault(location.name, {})[
                criterion.condition
            ] = ranges

    def check_weather_restriction(self, env, location, activity, activity_log, message):
        if location.name not in self.work_restrictions.keys():
            self.calc_work_restrictions(location)

        # if event_name in [criterion.event_name for criterion in self.criteria]:
        waiting = []

        for condition in self.work_restrictions[location.name]:
            ranges = self.work_restrictions[location.name][condition]

            t = datetime.datetime.fromtimestamp(env.now)
            t = pd.Timestamp(t).to_datetime64()
            i = ranges[:, 0].searchsorted(t)

            if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                waiting.append(pd.Timedelta(0).total_seconds())
            elif i + 1 < len(ranges):
                waiting.append(pd.Timedelta(ranges[i, 0] - t).total_seconds())
            else:
                raise AssertionError(
                    "\nSimulation cannot continue. Simulation time exceeded the available metocean data."
                )

        if waiting:
            return activity.delay_processing(env, message, activity_log, max(waiting))


class WeatherPluginMoveActivity(model.AbstractPluginClass, WorkabilityCriteriaMixin):
    """WeatherPluginMoveActivity is a class to allow to specify weather constraints to MoveActivities."""

    def __init__(
        self,
        metocean_criteria,
        metocean_data,
        activity,
        plugin_name="WeatherPluginMoveActivity",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.metocean_criteria = metocean_criteria
        self.work_restrictions = {}
        self.metocean_data = metocean_data

    def pre_process(self, env, origin, activity_log, message, activity):
        """
        Preprocess will checked whether the weather conditions are fulfilled.

        This is done at the time the move activity will be
        executed or whether the exdecution of the move activity has to be delayed.
        """

        activity_log.log_entry(
            message + " weather",
            env.now,
            -1,
            None,
            activity_log.id,
            core.LogState.UNKNOWN,
        )

        return self.check_weather_restriction(
            env, origin, activity, activity_log, message
        )

    def post_process(
        self,
        env,
        mover,
        origin,
        destination,
        engine_order,
        activity_log,
        message,
        activity,
        start_preprocessing,
        start_activity,
    ):
        """Post processing for the weather is not applicable."""
        pass


class HasWeatherPluginMoveActivity:
    """Mixin for MoveActivity to initialize WeatherPluginMoveActivity."""

    def __init__(
        self,
        metocean_criteria=None,
        metocean_df=None,
        timestep=10,
        bed=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if (
            metocean_criteria is not None
            and metocean_df is not None
            and isinstance(self, model.PluginActivity)
        ):
            self.timestep = datetime.timedelta(minutes=timestep)

            data = {}
            for key in metocean_df:
                series = (
                    pd.Series(metocean_df[key], index=metocean_df.index)
                    .fillna(0)
                    .resample(self.timestep)
                    .interpolate("linear")
                )

                data[key] = series.values

            data["Index"] = series.index
            self.metocean_data = pd.DataFrame.from_dict(data)
            self.metocean_data.index = self.metocean_data["Index"]
            self.metocean_data.drop(["Index"], axis=1, inplace=True)
            weather_plugin = WeatherPluginMoveActivity(
                metocean_criteria=metocean_criteria,
                metocean_data=self.metocean_data,
                activity=self,
            )
            self.register_plugin(plugin=weather_plugin, priority=2)
