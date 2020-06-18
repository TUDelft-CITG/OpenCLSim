import datetime, time
import simpy

# package(s) for data handling
import pandas as pd
import numpy as np

import openclsim.core as core
import openclsim.model as model


class TestPluginMoveActivity(model.AbstractPluginClass):
    """TestPluginMoveActivity is a class to generically test the plugin mechanism for MoveActivities."""

    def __init__(self, activity, plugin_name="TestPlugin"):
        super().__init__(plugin_name=plugin_name, activity=activity)

    def pre_process(
        self,
        env,
        mover,
        origin,
        destination,
        engine_order,
        activity_log,
        message,
        activity,
    ):
        """pre_process is a function which is called before the actual activity is executed. 
        The function may return a dictionary which may be processed by the activity before calling the next
        pre-processing function."""

        print(f"plugin_data mover: {mover}")
        print(f"plugin_data origin: {origin}")
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
        # return activity.delay_processing(env, message, activity_log, 20)
        return {}

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
        print(f"plugin_data mover: {mover}")
        print(f"plugin_data origin: {origin}")
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


class HasTestPluginMoveActivity:
    """Mixin for MoveActivity to initialize TestPluginMoveActivity"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self, model.PluginActivity):
            test_plugin = TestPluginMoveActivity(activity=self)
            self.register_plugin(plugin=test_plugin, priority=99)


class WeatherPluginMoveActivity(model.AbstractPluginClass):
    """WeatherPluginMoveActivity is a class to allow to specify weather constraints to MoveActivities."""

    def __init__(
        self,
        metocean_criteria,
        metocean_data,
        activity,
        plugin_name="WeatherPluginMoveActivity",
    ):
        super().__init__(plugin_name=plugin_name, activity=activity)
        self.metocean_criteria = metocean_criteria
        self.work_restrictions = {}
        self.metocean_data = metocean_data

    def pre_process(
        self,
        env,
        mover,
        origin,
        destination,
        engine_order,
        activity_log,
        message,
        activity,
    ):
        """pre_process will checked whether the weather conditions are fulfilled at the time the move activity will be
        executed or whether the exdecution of the move activity has to be delayed."""
        print("weatherPlugin start preprocess")

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

    def calc_work_restrictions(self, location):
        # Loop through series to find windows
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
            print(ranges)

            if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                waiting.append(pd.Timedelta(0).total_seconds())
            elif i + 1 < len(ranges):
                waiting.append(pd.Timedelta(ranges[i, 0] - t).total_seconds())
            else:
                print("\nSimulation cannot continue.")
                print("Simulation time exceeded the available metocean data.")
        print(waiting)
        if waiting:
            print(f"we have to wait for {max(waiting)}")
            # print(activity_log)
            # return self.delay_processing(env, message, activity_log, max(waiting))
            # print(f"delay processing {waiting}")
            # activity_log.log_entry(
            ##    message, env.now, -1, None, activity_log.id, core.LogState.WAIT_START,
            # )
            # print(f"before delay {env.now}")
            # yield env.timeout(max(waiting))
            # print(f"after delay {env.now}")
            # activity_log.log_entry(
            #    message, env.now, -1, None, activity_log.id, core.LogState.WAIT_STOP,
            # )
            return activity.delay_processing(env, message, activity_log, max(waiting))

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
        """post processing for the weather is not applicable."""

        pass


class HasWeatherPluginMoveActivity:
    """Mixin for MoveActivity to initialize WeatherPluginMoveActivity"""

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

        print("check weather plugin")
        print(metocean_criteria != None)
        print(metocean_df is not None)
        print(isinstance(self, model.PluginActivity))
        if (
            metocean_criteria != None
            and metocean_df is not None
            and isinstance(self, model.PluginActivity)
        ):
            print("regrister weather plugin")
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


class WeatherPluginShiftAmountActivity(model.AbstractPluginClass):
    """WeatherPluginShiftAmountActivity is a class to allow to specify weather constraints to MoveActivities."""

    def __init__(
        self,
        metocean_criteria,
        metocean_data,
        activity,
        plugin_name="WeatherPluginShiftAmountActivity",
    ):
        super().__init__(plugin_name=plugin_name, activity=activity)
        self.metocean_criteria = metocean_criteria
        self.work_restrictions = {}
        self.metocean_data = metocean_data

    def pre_process(
        self,
        env,
        origin,
        activity_log,
        message,
        activity,
        processor,
        destination,
        engine_order,
        duration,
        amount,
    ):
        """pre_process will checked whether the weather conditions are fulfilled at the time the move activity will be
        executed or whether the exdecution of the move activity has to be delayed."""
        print("weatherPlugin start preprocess")
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

    def calc_work_restrictions(self, location):
        # Loop through series to find windows
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
            print(ranges)

            if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                waiting.append(pd.Timedelta(0).total_seconds())
            elif i + 1 < len(ranges):
                waiting.append(pd.Timedelta(ranges[i, 0] - t).total_seconds())
            else:
                print("\nSimulation cannot continue.")
                print("Simulation time exceeded the available metocean data.")
        print(waiting)
        if waiting:
            print(f"we have to wait for {max(waiting)}")
            return activity.delay_processing(env, message, activity_log, max(waiting))

    def post_process(
        self,
        env,
        origin,
        activity_log,
        message,
        activity,
        processor,
        destination,
        engine_order,
        duration,
        amount,
        start_preprocessing,
        start_activity,
    ):
        """post processing for the weather is not applicable."""

        pass


class HasWeatherPluginShiftAmountActivity:
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

        print("check weather plugin")
        print(metocean_criteria != None)
        print(metocean_df is not None)
        print(isinstance(self, model.PluginActivity))
        if (
            metocean_criteria != None
            and metocean_df is not None
            and isinstance(self, model.PluginActivity)
        ):
            print("regrister weather plugin")
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
            weather_plugin = WeatherPluginShiftAmountActivity(
                metocean_criteria=metocean_criteria,
                metocean_data=self.metocean_data,
                activity=self,
            )
            self.register_plugin(plugin=weather_plugin, priority=2)
