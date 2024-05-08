#!/usr/bin/env python3

"""Directory for the depth plugin."""

import numpy as np
import pandas as pd
import logging

import openclsim.model


logger = logging.getLogger(__name__)

def water_level(t, amplitude=1.5):
    """simple tidal water level function for demo applications

    Parameters
    ----------
    t : float
        time in hours
    """
    # t is in hours
    tidal_phase = 0
    tidal_period = 12.42
    water_level_at_t = amplitude * np.sin(2 * np.pi * t / tidal_period - tidal_phase)
    return water_level_at_t


def compute_tidal_windows(water_level, t_now, t_max, threshold):
    """
    Compute tidal windows based on a water level function

    Parameters
    ----------
    water_level : callable
        a function that takes a time in hours and returns a water level
    t_now : float
        the current time (suggestion: env.now / 3600)
    t_max : float
        the maximum time window ahead to consider
    threshold : float
        the threshold for the water level

    """
    # timesteps in minutess
    t = np.arange(t_now, t_now + t_max, 1 / 60)
    # compute or lookup  waterlevels for each minute
    water_levels = water_level(t)

    # find all roots where water level changes over our threshold
    tidal_switch_idx = np.diff(water_level(t) > threshold)
    print("switch", tidal_switch_idx)
    if not np.any(tidal_switch_idx):
        # no tidal windows found, let's use the whole window
        selected_t = [t[-1]]
        selected_water_level = [water_levels[-1]]
    else:

        # these are all the roots of our water level function
        selected_t = (t[:-1][tidal_switch_idx] + t[1:][tidal_switch_idx]) / 2
        selected_water_level = (water_levels[:-1][tidal_switch_idx] + water_levels[1:][tidal_switch_idx]) / 2

    # lets' evaluate all tidal windows
    # we could optimize by stopping once we found a valid tidal window
    pairs = []
    pairs.append((t_now, selected_t[0]))
    for a, b in zip(selected_t[:-1], selected_t[1:]):
        pair = (a, b)
        pairs.append(pair)


    rows = []
    for pair in pairs:
        t0, t1 = pair
        t_middle = (pair[0] + pair[1]) / 2
        water_level_middle = water_level(t_middle)
        water_level_t0 = water_level(t0)
        water_level_t1 = water_level(t1)
        tide_allows = water_level_middle  > threshold
        row = {}
        row['tide_allows'] = tide_allows
        row['t0'] = t0
        row['t1'] = t1
        row['t_middle'] = t_middle
        row['water_level_middle'] = water_level_middle
        row['water_level_t0'] = water_level_t0
        row['water_level_t1'] = water_level_t1
        rows.append(row)

    tidal_windows_df = pd.DataFrame(rows)
    tidal_windows_df
    return tidal_windows_df


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


class TideCriterion:
    """
    Used to add determine if a vessel can start sailing based on the tide

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

    def __init__(self, dredge_criteria, destination, *args, **kwargs):
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


class TidePluginActivity(openclsim.model.AbstractPluginClass):
    """Mixin for ShiftAmountActivity to initialize ShiftAmountActivity."""

    def __init__(
        self,
        tide_criteria,
        destination,
        mover,
        actual_water_level=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        assert isinstance(tide_criteria, TideCriterion)
        self.tide_criteria = tide_criteria
        self.destination = destination
        self.mover = mover
        self.actual_water_level = actual_water_level

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        print("check tidal criteria", env.now)

        if self.tide_criteria is not None:
            print("wait until we tidal window allows to sail")
            activity_label = {"type": "plugin", "ref": "tide"}
            waiting = self.time_until_tide_allows(env)
            print(f"waiting for {waiting} seconds")
            print("activity log", activity_log)
            return activity.delay_processing(env, activity_label, activity_log, waiting)
        else:
            return {}

    def tide_allows(self):
        logger.info("True if we tidal window allows to sail")
        print(self.actual_water_level, self.destination.MBL)
        available_water_depth = self.actual_water_level - self.destination.MBL
        gross_ukc = available_water_depth - self.vessel.T

        if gross_ukc > 0:
            print("we have positive under keel clearance")
            return True
        else:
            print("we do not have positive under keel clearance")
            return False

    def time_until_tide_allows(self, env):
        """compute how long until next tidal window opportunity"""
        t_now = env.now / 3600 # current time in hours
        t_max = 12.42 * 4 # 4 tidal periods ahead
        # the needed available water level at our destination
        threshold = self.destination.ABL + self.mover.UKC + self.mover.T
        print(
            "threshold", threshold,
            "ABL", self.destination.ABL,
            "UKC", self.mover.UKC,
            "T", self.mover.T
        )


        tidal_windows_df = compute_tidal_windows(openclsim.plugins.access.water_level, t_now, t_max, threshold)
        selected_windows = tidal_windows_df[tidal_windows_df.tide_allows]
        selected_window = selected_windows.iloc[0]
        time_to_start_sailing = (selected_window.t0 * 3600)
        delay = time_to_start_sailing - env.now
        return delay

    def process_data(self, criterion) -> dict:
        result: dict = {}
        return result


class HasDredgePluginActivity(openclsim.model.MoveActivity):
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


class HasTidePluginActivity(openclsim.model.MoveActivity):
    """Mixin for Activity to initialize TidePluginActivity."""

    def __init__(self, tide_criteria, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert hasattr(self, "destination"), f"{self} should have a destination"
        destination = self.destination
        assert hasattr(self, "mover"), f"{self} should have a mover"
        mover = self.mover

        if tide_criteria is not None and isinstance(
            self, openclsim.model.PluginActivity
        ):
            tide_plugin = TidePluginActivity(tide_criteria=tide_criteria, destination=destination, mover=mover)
            self.register_plugin(plugin=tide_plugin, priority=2)
