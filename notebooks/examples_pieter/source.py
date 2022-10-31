import datetime
import time

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import simpy
from plotly.offline import init_notebook_mode, iplot
from shapely import geometry

import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugin
import openclsim.utils as utils
import abc


def get_current_depth(env):
    df = env.depth_data
    now = env.now
    now_diff = min((df["ts"] - now).abs())
    now_row = next(row for i, row in df.iterrows() if abs(row["ts"] - now) == now_diff)
    min_depth = now_row["Minimum depth"]
    return min_depth


class BaseDecisionmaker(abc.ABC):
    """decisionmaker base class for the decide activity."""

    @abc.abstractmethod
    def decide():
        return None


class DepthRestrictedLoadingFunctions:
    def __init__(
        self,
        unloading_rate: float,
        loading_rate: float,
        depth_empty: float,
        depth_full: float,
        unload_manoeuvring: float = 0,
        load_manoeuvring: float = 0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.unloading_rate = unloading_rate
        self.unload_manoeuvring = unload_manoeuvring
        self.loading_rate = loading_rate
        self.load_manoeuvring = load_manoeuvring
        self.depth_empty = depth_empty
        self.depth_full = depth_full

    def get_depth_restricted_load(self):
        min_depth = get_current_depth(self.env)
        amount = (
            self.container.get_capacity()
            * (min_depth - self.depth_empty)
            / (self.depth_full - self.depth_empty)
        )
        return round(amount, 6)

    def loading(self, origin, destination, amount, id_="default"):
        depth_restricted_load = self.get_depth_restricted_load()
        amount = min(amount, depth_restricted_load)
        if not hasattr(self.loading_rate, "__call__"):
            duration = amount / self.loading_rate + self.load_manoeuvring * 60
            return duration, amount
        else:
            loading_time = self.loading_rate(
                destination.container.get_level(id_),
                destination.container.get_level(id_) + amount,
            )
            duration = loading_time + self.load_manoeuvring * 60
            return duration, amount

    def unloading(self, origin, destination, amount, id_="default"):
        if not hasattr(self.unloading_rate, "__call__"):
            duration = amount / self.unloading_rate + self.unload_manoeuvring * 60
            return duration, amount
        else:
            unloading_time = self.unloading_rate(
                origin.container.get_level(id_) + amount,
                origin.container.get_level(id_),
            )
            duration = unloading_time + self.unload_manoeuvring * 60
            return duration, amount


class DecideActivity(model.GenericActivity):
    """DecideActivity Class forms a specific class."""

    key = "DecideActivity"

    def __init__(self, decide_arguments, decision_maker, *args, **kwargs):
        """Initialise the activity."""

        super().__init__(*args, **kwargs)

        self.decide_arguments = decide_arguments
        self.decision_maker = decision_maker

    def choose_subprocess(self):
        self.sub_process = self.decision_maker.decide(**self.decide_arguments)
        if self.sub_process:
            model.register_processes(self.sub_process)

    def main_process_function(self, activity_log, env):
        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_time_decide = env.now
        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        self.choose_subprocess()
        if self.sub_process:
            yield self.parse_expression(
                {"type": "activity", "state": "done", "name": self.sub_process.name}
            )

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )
        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_time_decide
        yield from self.post_process(**args_data)


Site = type(
    "Site",
    (
        core.Identifiable,
        core.Log,
        core.Locatable,
        core.HasContainer,
        core.HasResource,
    ),
    {},
)

TransportProcessingResource = type(
    "TransportProcessingResource",
    (
        core.Identifiable,
        core.Log,
        core.ContainerDependentMovable,
        core.Processor,
        core.HasResource,
        DepthRestrictedLoadingFunctions,
    ),
    {},
)

TestMoveActivity = type(
    "TestMoveActivity",
    (
        plugin.HasDepthPluginActivity,
        model.MoveActivity,  # the order is critical!
    ),
    {},
)

TestShiftActivity = type(
    "TestShiftActivity",
    (
        plugin.HasDepthPluginActivity,
        model.ShiftAmountActivity,  # the order is critical!
    ),
    {},
)


def get_dataframe():
    df = pd.DataFrame(
        index=pd.date_range(
            start="2018-08-01 00:00:00", end="2019-08-01 00:00:00", freq="H"
        )
    )
    df.apply(lambda row: row.index.dt.timestamp())
    df["ts"] = df.index.values.astype(float) / 1_000_000_000
    df["Minimum depth"] = np.sin(1 / 12 * df["ts"] / 3600 * np.pi) + 1.5
    df["Time"] = df.index
    return df


def spawn_cycle(
    registry,
    env,
    vessel,
    origin,
    destination,
    sailing_crit,
    loading_crit,
    df,
):
    sub_processes = [
        TestMoveActivity(
            env=env,
            name=f"sailing empty {vessel.name} {env.now}",
            registry=registry,
            mover=vessel,
            destination=origin,
            depth_criteria=sailing_crit,
            depth_df=df,
        ),
        TestShiftActivity(
            env=env,
            name=f"loading {vessel.name} {env.now}",
            registry=registry,
            origin=origin,
            destination=vessel,
            processor=vessel,
            depth_criteria=loading_crit,
            depth_df=df,
            phase="loading",
            amount=4,
        ),
        TestMoveActivity(
            env=env,
            name=f"sailing full {vessel.name} {env.now}",
            registry=registry,
            mover=vessel,
            destination=destination,
            depth_criteria=sailing_crit,
            depth_df=df,
        ),
        TestShiftActivity(
            env=env,
            name=f"unloading {vessel.name} {env.now}",
            registry=registry,
            processor=vessel,
            origin=vessel,
            destination=destination,
            depth_criteria=loading_crit,
            depth_df=df,
            phase="unloading",
            amount=4,
        ),
    ]

    sequential_activity = model.SequentialActivity(
        env=env,
        name=f"sequential_activity_subcycle {vessel.name} {env.now}",
        registry=registry,
        sub_processes=sub_processes,
    )
    return sequential_activity


class WatchTower(BaseDecisionmaker):
    def __init__(
        self,
        name,
        env,
        large_depth_treshold,
        large_vessels,
        sailing_crit_large,
        loading_crit_large,
        small_vessels,
        sailing_crit_small,
        loading_crit_small,
        registry,
        from_site,
        to_site,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        self.env = env
        self.large_depth_treshold = large_depth_treshold
        self.large_vessels = large_vessels
        self.sailing_crit_large = sailing_crit_large
        self.loading_crit_large = loading_crit_large
        self.small_vessels = small_vessels
        self.sailing_crit_small = sailing_crit_small
        self.loading_crit_small = loading_crit_small
        self.registry = registry
        self.from_site = from_site
        self.to_site = to_site

    def decide(self):
        if (
            self.to_site.container.get_level("default_reservations")
            < self.to_site.container.get_capacity()
        ):
            return self.decide_cycle()
        return None

    def decide_cycle(self):
        min_depth = get_current_depth(self.env)
        decide_activity = DecideActivity(
            env=self.env,
            name=f"Decide {self.env.now}",
            registry=self.registry,
            decision_maker=self,
            decide_arguments={},
        )
        if min_depth >= self.large_depth_treshold:
            sub_processes = [
                spawn_cycle(
                    self.registry,
                    self.env,
                    vessel,
                    self.from_site,
                    self.to_site,
                    self.sailing_crit_large,
                    self.loading_crit_large,
                    self.env.depth_data,
                )
                for vessel in self.large_vessels
            ]
        else:
            sub_processes = [
                spawn_cycle(
                    self.registry,
                    self.env,
                    vessel,
                    self.from_site,
                    self.to_site,
                    self.sailing_crit_small,
                    self.loading_crit_small,
                    self.env.depth_data,
                )
                for vessel in self.small_vessels
            ]
        return model.SequentialActivity(
            env=self.env,
            registry=self.registry,
            name=f"cycle load {self.env.now}",
            sub_processes=[
                model.ParallelActivity(
                    env=self.env,
                    registry=self.registry,
                    name=f"cycle parallel {self.env.now}",
                    sub_processes=sub_processes,
                ),
                decide_activity,
            ],
        )
