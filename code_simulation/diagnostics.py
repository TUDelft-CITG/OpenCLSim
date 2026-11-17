"""Checks on a finished simulation run.

weather_gate_report(result)
    OpenCLSim's weather plugin lets a weather-gated activity start *at once*
    when the metocean series holds no workable window of the required length
    after the current time, and also once the simulation runs past the end
    of the series. For long tows (window = full sailing time) this can hide
    weather delay. This report checks every start of every weather-gated
    activity against the series:

    ok           violation flag is 0 over [start, start + window_length)
    no_window    the window contained a violation (start was not gated)
    beyond_data  start + window_length lies after the end of the series

    Each hourly record is taken to hold until the next one, as in OpenCLSim's
    window search. A window of length zero (a tow over 0 km) is always "ok".
    A run whose report shows only "ok" is gated as intended.
"""

import re

import numpy as np
import pandas as pd

import openclsim.model as model
from openclsim.plugins.weather import WeatherPluginActivity

from analysis import get_activity_log


def _all_activities(result):
    tops = []
    for value in result.activities.values():
        tops.extend(value if isinstance(value, list) else [value])
    seen, out = set(), []
    for act in model.get_subprocesses(tops):
        if id(act) not in seen:
            seen.add(id(act))
            out.append(act)
    return out


def _epoch(ts):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.timestamp()


def weather_gate_report(result):
    """DataFrame with, per weather-gated activity, how its starts were gated."""
    rows = []
    for act in _all_activities(result):
        weather = [p["plugin"] for p in getattr(act, "plugins", [])
                   if isinstance(p["plugin"], WeatherPluginActivity)]
        if not weather:
            continue
        log = get_activity_log(act)
        if log.empty:
            continue
        starts = np.array([_epoch(t) for t in log["start"]])
        for plug in weather:
            crit = plug.weather_criteria
            df = plug.metocean_df
            ts = df["ts"].to_numpy(dtype=float)
            values = df[crit.condition].to_numpy(dtype=float)
            if crit.maximum is not None:
                bad = values > crit.maximum
            else:
                bad = values < crit.minimum
            length = crit.window_length + crit.window_delay
            step = ts[-1] - ts[-2] if len(ts) > 1 else 3600.0
            lo = np.maximum(np.searchsorted(ts, starts + 1e-6, side="right") - 1, 0)
            hi = np.searchsorted(ts, starts + length - 1e-6, side="left")
            hi = np.maximum(hi, lo + 1)
            beyond = starts + length > ts[-1] + step
            if length > 0:
                violated = np.array([bad[a:b].any() for a, b in zip(lo, hi)])
            else:
                violated = np.zeros(len(starts), dtype=bool)
            rows.append({
                "activity": re.sub(r"\s*\[(FC|TUG|TC)\d+\]$", "", act.name),
                "criterion": crit.condition,
                "window_h": round(length / 3600, 2),
                "starts": len(starts),
                "ok": int((~beyond & ~violated).sum()),
                "no_window": int((~beyond & violated).sum()),
                "beyond_data": int(beyond.sum()),
            })
    if not rows:
        return pd.DataFrame(columns=["activity", "criterion", "window_h", "starts",
                                     "ok", "no_window", "beyond_data"])
    report = (pd.DataFrame(rows)
              .groupby(["activity", "criterion", "window_h"], as_index=False)
              [["starts", "ok", "no_window", "beyond_data"]].sum())
    return report.sort_values("activity").reset_index(drop=True)


def print_weather_gate_report(result):
    report = weather_gate_report(result)
    print(report.to_string(index=False))
    bad = report[(report["no_window"] > 0) | (report["beyond_data"] > 0)]
    if bad.empty:
        print("\nAll weather-gated starts had a workable window.")
    else:
        print(f"\n{int(bad['no_window'].sum())} start(s) without a workable window, "
              f"{int(bad['beyond_data'].sum())} beyond the metocean data.")
    return report
