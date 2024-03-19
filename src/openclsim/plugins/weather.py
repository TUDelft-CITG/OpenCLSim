"""Directory for the weather plugin."""

from typing import Optional

import numpy as np

import openclsim.model as model


class WeatherCriterion:
    """
    Used to add limits to vessels (and therefore acitivities).

    Parameters
    ----------
    condition
        Column of the climate table
    window_length : minutes
        Lenght of the window in minutes
    window_delay : minutes
        Delay of the window compared to the start of the activity
    maximum
        maximal value of the condition
    minimum
        minimum value of the condition
    """

    def __init__(
        self,
        name: str,
        condition: str,
        window_length: float,
        maximum: Optional[float] = None,
        minimum: Optional[float] = None,
        window_delay: float = 0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        self.condition = condition

        try:
            assert (maximum is not None) or (minimum is not None)
            if minimum is not None:
                assert maximum is None
            if maximum is not None:
                assert minimum is None
        except Exception as e:
            raise AssertionError(
                "One and only one of the parameters minimum or maximum can be "
                f"defined (error message: {e})."
            )

        self.minimum = minimum
        self.maximum = maximum

        self.window_length = window_length
        self.window_delay = window_delay


class HasWeatherPluginActivity:
    """Mixin for Activity to initialize WeatherPluginActivity."""

    def __init__(self, metocean_criteria, metocean_df, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            metocean_criteria is not None
            and metocean_df is not None
            and isinstance(self, model.PluginActivity)
        ):
            self.metocean_data = metocean_df

            weather_plugin = WeatherPluginActivity(
                weather_criteria=metocean_criteria, metocean_df=self.metocean_data
            )
            self.register_plugin(plugin=weather_plugin, priority=2)


class WeatherPluginActivity(model.AbstractPluginClass):
    """Mixin for MoveActivity to initialize TestPluginMoveActivity."""

    def __init__(self, weather_criteria=None, metocean_df=None):
        assert isinstance(weather_criteria, WeatherCriterion)
        self.weather_criteria = weather_criteria
        self.metocean_df = metocean_df

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        if self.weather_criteria is not None:
            t = float(env.now)
            determined_range = self.check_constraint(start_time=t)

            if not isinstance(determined_range, list):
                raise AssertionError

            elif t < determined_range[0]:
                activity_label = {"type": "plugin", "ref": "waiting on weather"}
                waiting = determined_range[0] - t
                return activity.delay_processing(
                    env, activity_label, activity_log, waiting
                )
            else:
                return {}
        else:
            return {}

    def check_constraint(self, start_time):
        res = self.process_data(self.weather_criteria)
        windows = np.array(res["windows"])
        ts_start = res["dataset_start"]
        ts_stop = res["dataset_stop"]

        filter_windows = windows[windows[:, 1] >= start_time]
        i = 0
        while len(filter_windows) < 1 and i < 10:
            dt = i * (ts_stop - ts_start)
            filter_windows = windows[windows[:, 1] >= start_time - dt]
            i = i + 1

        return list(filter_windows[0])

    def process_data(self, criterion) -> dict:
        col = criterion.condition
        orig_data = self.metocean_df.copy()

        # get start and stop date of the data set
        ts_start = min(orig_data["ts"])
        ts_stop = max(orig_data["ts"])

        data = orig_data.copy()
        data["ts"] = data["ts"]
        data["cur"] = True
        data["prev_ts"] = data.ts.shift(1)

        if criterion.maximum is not None:
            threshold = {col: criterion.maximum}

            if orig_data[col].max() < threshold[col]:
                return {
                    "dataset_start": ts_start,
                    "dataset_stop": ts_stop,
                    "windows": [[ts_start, ts_stop]],
                }

            data["cur"] = data["cur"] & (data[col] <= threshold[col])
            data[f"{col}_prev"] = data[col].shift(1)

            data[f"{col}_inter"] = data["ts"]
        else:
            threshold = {col: criterion.minimum}

            if orig_data[col].min() > threshold[col]:
                return {
                    "dataset_start": ts_start,
                    "dataset_stop": ts_stop,
                    "windows": [[ts_start, ts_stop]],
                }

            data["cur"] = data["cur"] & (data[col] >= threshold[col])
            data[f"{col}_prev"] = data[col].shift(1)
            data[f"{col}_inter"] = data["ts"]

        data["prev"] = data.cur.shift(1)
        data = data[1:]
        data = data[data.cur ^ data.prev]
        data["type"] = "start"

        data[f"{col}_inter"] = data.ts
        data2 = data.loc[(data[col] - data[f"{col}_prev"]) != 0]
        data2[f"{col}_inter"] = data2.prev_ts + (data2.ts - data2.prev_ts) * (
            threshold[col] - data2[f"{col}_prev"]
        ) / (data2[col] - data2[f"{col}_prev"])
        if criterion.maximum is not None:
            data.loc[data[col] > threshold[col], "type"] = "end"
        else:
            data.loc[data[col] < threshold[col], "type"] = "end"

        columns = [f"{col}_inter"]
        data["ts_inter"] = np.maximum.reduce(data[columns].values, axis=1)
        data["end_inter"] = data.ts_inter.shift(-1)

        if data.iloc[0]["type"] == "end":
            data.iloc[0, data.columns.get_loc("type")] = "start"
            data.iloc[0, data.columns.get_loc("end_inter")] = data.iloc[0]["ts_inter"]
            data.iloc[0, data.columns.get_loc("ts_inter")] = orig_data.iloc[0]["ts"]
        if data.iloc[-1]["type"] == "start":
            data.iloc[-1, data.columns.get_loc("end_inter")] = orig_data.iloc[-1]["ts"]

        data.rename(columns={"ts_inter": "start_inter"}, inplace=True)

        data = data[data["type"] == "start"][["start_inter", "end_inter"]]

        data = data[data["end_inter"] - data["start_inter"] > criterion.window_length]
        data["end_inter"] = (
            data["end_inter"] - criterion.window_length - criterion.window_delay
        )
        data["start_inter"] = data["start_inter"] - criterion.window_delay
        windows = [list(data.iloc[d]) for d in range(len(data))]

        result = {
            "dataset_start": ts_start,
            "dataset_stop": ts_stop,
            "windows": windows,
        }
        return result
