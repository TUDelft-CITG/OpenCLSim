"""Post-processing: per-turbine timelines (Gantt), phase statistics and plots.

The simulation tracks floaters and turbines as anonymous container units.
Per-turbine timelines are reconstructed first in, first out: the i-th floater
produced is assumed to be the i-th launched, towed, integrated, installed and
commissioned. This only affects per-turbine phase durations, not the total
installation time.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import openclsim.model as model

import config as cfg


def get_activity_log(activity):
    """START/STOP pairs of one activity as a DataFrame (one row per execution)."""
    log = activity.log
    if not log["Timestamp"]:
        return pd.DataFrame()
    df = pd.DataFrame({
        "timestamp": log["Timestamp"],
        "state": log["ActivityState"],
    })
    starts = df[df["state"] == "START"].reset_index(drop=True)
    stops = df[df["state"] == "STOP"].reset_index(drop=True)
    n = min(len(starts), len(stops))
    return pd.DataFrame({
        "start": starts["timestamp"][:n],
        "stop": stops["timestamp"][:n],
        "activity": activity.name,
    })


def find_sub(repeat_act, name_contains):
    """First (sub)activity whose name contains name_contains (case-insensitive)."""
    for sub in model.get_subprocesses(repeat_act):
        if name_contains.lower() in sub.name.lower():
            return sub
    raise ValueError(f"Sub-activity not found: {name_contains}")


def find_all_subs(repeat_act, name_contains):
    matches = [sub for sub in model.get_subprocesses(repeat_act)
               if name_contains.lower() in sub.name.lower()]
    if not matches:
        raise ValueError(f"Sub-activity not found: {name_contains}")
    return matches


def merged_leg_log(activity_list, name_contains):
    """Log of one step over all parallel vessels of a leg, sorted by start."""
    frames = []
    for act in activity_list:
        sub = find_sub(act, name_contains)
        frames.append(get_activity_log(sub))
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("start").reset_index(drop=True)
    return merged


def _utc(df):
    """Make the start/stop columns timezone-aware (UTC)."""
    for col in ("start", "stop"):
        if col in df.columns and len(df) > 0 and df[col].dt.tz is None:
            df[col] = df[col].dt.tz_localize("UTC")
    return df


def _commissioning_rows(act, anchors_df):
    """Waiting-for-CLV, TT&E and hot-commissioning bars per turbine.

    One CLV commissions the turbines one at a time, in the order in which
    their IAC hook-up finishes (FIFO via installed_queue). So the k-th turbine
    to finish IAC hook-up is the k-th one the CLV claims, and its TT&E and WTG
    shifts are the ones between that claim and the matching release. Time
    between IAC hook-up and the claim is queueing for the CLV.
    """
    string = act["stringing_activity"]
    claims = _utc(get_activity_log(find_sub(string, "claim installed turbine")))
    releases = _utc(get_activity_log(find_sub(string, "release commissioned turbine")))
    tte_log = _utc(get_activity_log(find_sub(string, "[SE]TTE at site")))
    wtg_log = _utc(get_activity_log(find_sub(string, "[SE]WTG commissioning at site")))
    if len(claims) == 0:
        return []
    claims = claims.sort_values("start").reset_index(drop=True)
    releases = releases.sort_values("start").reset_index(drop=True)

    iac = (anchors_df[["turbine_id", "installed2_stop"]]
           .dropna().sort_values("installed2_stop").reset_index(drop=True))

    rows = []
    for k, (tid, iac_stop) in enumerate(zip(iac["turbine_id"], iac["installed2_stop"])):
        if k >= len(claims):
            break
        claim = claims.loc[k, "stop"]
        if k < len(releases):
            upper = releases.loc[k, "stop"]
        elif k + 1 < len(claims):
            upper = claims.loc[k + 1, "start"]
        else:
            upper = pd.Timestamp.max.tz_localize("UTC")

        if claim > iac_stop:
            rows.append({
                "turbine_id": tid, "phase": "Waiting for CLV",
                "start": iac_stop, "stop": claim,
                "duration_h": (claim - iac_stop).total_seconds() / 3600,
            })

        tte = tte_log[(tte_log["start"] >= claim) & (tte_log["stop"] <= upper)]
        tte_stop = pd.NaT
        if len(tte) > 0:
            tte_stop = tte["stop"].max()
            if tte_stop > claim:
                rows.append({
                    "turbine_id": tid, "phase": "TT&E",
                    "start": claim, "stop": tte_stop,
                    "duration_h": (tte_stop - claim).total_seconds() / 3600,
                    "active_h": ((tte["stop"] - tte["start"])
                                 .dt.total_seconds() / 3600).sum(),
                    "n_shifts": len(tte),
                })

        wtg_start = tte_stop if pd.notna(tte_stop) else claim
        wtg = wtg_log[(wtg_log["start"] >= wtg_start) & (wtg_log["stop"] <= upper)]
        if len(wtg) > 0:
            wtg_stop = wtg["stop"].max()
            if wtg_stop > wtg_start:
                rows.append({
                    "turbine_id": tid, "phase": "Hot commissioning",
                    "start": wtg_start, "stop": wtg_stop,
                    "duration_h": (wtg_stop - wtg_start).total_seconds() / 3600,
                    "active_h": ((wtg["stop"] - wtg["start"])
                                 .dt.total_seconds() / 3600).sum(),
                    "n_shifts": len(wtg),
                })
    return rows


def build_turbine_tracking_df(result):
    """Per-turbine phase table (Gantt rows) and the underlying anchor times.

    Returns (gantt_df, anchors_df). gantt_df has one row per turbine and
    phase with columns turbine_id, phase, start, stop, duration_h (plus
    active_h and n_shifts for the shift-based commissioning phases).
    """
    act = result.activities
    n_turbines = cfg.N_TARGET

    anchor_times = {
        "production_work":
            get_activity_log(find_sub(act["production_activity"], "manufacturing floater")),
        "production_done":
            get_activity_log(find_sub(act["production_activity"], "floater into stockyard")),
        "launch_start":
            get_activity_log(find_sub(act["launch_activity"], "[WW] launching 1 floater")),
        "launched":
            get_activity_log(find_sub(act["launch_activity"], "floater 1 into water")),
        "at_ws1":
            get_activity_log(find_sub(act["launch_activity"], "floater into wet storage 1")),
        "loaded_at_berth":
            merged_leg_log(act["floater_leg_activities"], "loading 1 floater from launch berth"),
        "at_wet_storage":
            merged_leg_log(act["floater_leg_activities"], "delivering floater at wet storage"),
        "tug_pickup":
            merged_leg_log(act["tug_leg_activities"], "tug picks up floater from wet storage"),
        "at_integration":
            merged_leg_log(act["tug_leg_activities"], "tug delivers floater at berth IP1"),
        "assembly_intake":
            get_activity_log(find_sub(act["assembly_activity_A"], "move floater from pre-integration to integration quay")),
        "assembly_handover":
            get_activity_log(find_sub(act["assembly_activity_A"], "handover to mid-buffer")),
        "commissioning_intake":
            get_activity_log(find_sub(act["assembly_activity_B"], "intake from mid-buffer")),
        "commissioning_work":
            get_activity_log(find_sub(act["assembly_activity_B"], "commissioning & testing")),
        "at_ws3":
            get_activity_log(find_sub(act["assembly_activity_B"], "release commissioned turbine to wet storage 3")),
        "tc_loaded":
            merged_leg_log(act["turbine_leg_activities"], "[SE]loading integrated turbine"),
        "tc_offloaded":
            merged_leg_log(act["turbine_leg_activities"], "[SE]offloading turbine at site"),
        "installed1":
            merged_leg_log(act["turbine_leg_activities"], "[SE]installation at site"),
        "installed2":
            merged_leg_log(act["turbine_leg_activities"], "signal: installation done -> installed_queue"),
    }

    turbine_anchors = []
    for i in range(n_turbines):
        row = {"turbine_id": i + 1}
        for key, df in anchor_times.items():
            if i < len(df):
                row[f"{key}_start"] = df.loc[i, "start"]
                row[f"{key}_stop"] = df.loc[i, "stop"]
            else:
                row[f"{key}_start"] = pd.NaT
                row[f"{key}_stop"] = pd.NaT
        turbine_anchors.append(row)
    anchors_df = pd.DataFrame(turbine_anchors)

    for col in anchors_df.columns:
        if col.endswith("_start") or col.endswith("_stop"):
            if anchors_df[col].dtype.kind == "M":
                if anchors_df[col].dt.tz is None:
                    anchors_df[col] = anchors_df[col].dt.tz_localize("UTC")

    phase_defs = [
        ("Produced floater in stockyard",      "production_work_start",      "launched_start"),
        ("Float-off",                          "launched_start",             "at_ws1_stop"),
        ("Buffer berth 1",                     "at_ws1_stop",                "loaded_at_berth_start"),
        ("Tow floater to wet storage",         "loaded_at_berth_start",      "at_wet_storage_start"),
        ("Wet storage",                        "at_wet_storage_start",       "tug_pickup_start"),
        ("Tow floater to integration port",    "tug_pickup_start",           "at_integration_stop"),
        ("Buffer berth 2",                     "at_integration_stop",        "assembly_intake_start"),
        ("Turbine integration & WTG assembly", "assembly_intake_start",      "commissioning_intake_start"),
        ("Cold commissioning",                 "commissioning_intake_start", "at_ws3_stop"),
        ("Buffer berth 3",                     "at_ws3_stop",                "tc_loaded_start"),
        ("Tow-out to project site",            "tc_loaded_start",            "tc_offloaded_stop"),
        ("Mooring hookup",                     "tc_offloaded_stop",          "installed1_stop"),
        ("IAC hookup",                         "installed1_stop",            "installed2_stop"),
    ]

    rows = []
    for _, t in anchors_df.iterrows():
        for phase, start_col, stop_col in phase_defs:
            start, stop = t[start_col], t[stop_col]
            if pd.notna(start) and pd.notna(stop) and stop > start:
                rows.append({
                    "turbine_id": t["turbine_id"],
                    "phase": phase,
                    "start": start,
                    "stop": stop,
                    "duration_h": (stop - start).total_seconds() / 3600,
                })

    rows += _commissioning_rows(act, anchors_df)

    return pd.DataFrame(rows), anchors_df


_PHASE_COLORS = {
    "Produced floater in stockyard":             "#06548c",
    "Float-off":                                 "#79bdd5",
    "Buffer berth 1":                            "#d7fffc",
    "Tow floater to wet storage":                "#36b736",
    "Wet storage":                               "#ed89dc",
    "Tow floater to integration port":           "#36b736",
    "Buffer berth 2":                            "#feb4b4",
    "Turbine integration & WTG assembly":        "#ff0000",
    "Cold commissioning":                        "#ff6565",
    "Buffer berth 3":                            "#f7afaf",
    "Tow-out to project site":                   "#36b736",
    "Mooring hookup":                            "#bdaa00a8",
    "IAC hookup":                                "#ffe600",
    "Waiting for CLV":                           "#c8c8c8",
    "TT&E":                                      "#fced6b",
    "Hot commissioning":                         "#fffaa0",
}

_PHASE_ORDER = list(_PHASE_COLORS.keys())


def plot_turbine_gantt(df, turbine_ids=None, figsize=(14, 10)):
    """Gantt chart with one bar row per turbine."""
    if turbine_ids is None:
        turbine_ids = sorted(df["turbine_id"].unique())

    phases = [p for p in _PHASE_ORDER if p in df["phase"].unique()]

    fig, ax = plt.subplots(figsize=figsize)
    for y, tid in enumerate(turbine_ids):
        sub = df[df["turbine_id"] == tid]
        for _, row in sub.iterrows():
            ax.barh(
                y,
                row["stop"] - row["start"],
                left=row["start"],
                color=_PHASE_COLORS.get(row["phase"], "#888888"),
                edgecolor="black", linewidth=0.2, height=0.7,
            )

    ax.set_yticks(range(len(turbine_ids)))
    ax.set_yticklabels([f"Turbine {t}" for t in turbine_ids])
    ax.invert_yaxis()
    ax.set_xlabel("Time")

    total_days = (df["stop"].max() - df["start"].min()).total_seconds() / 86400
    ax.set_title(f"Gantt chart per turbine (N={len(turbine_ids)}), "
                 f"total duration {total_days:.0f} d ({total_days / 365:.2f} years)")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="x", alpha=0.3)

    handles = [plt.Rectangle((0, 0), 1, 1, color=_PHASE_COLORS[p]) for p in phases]

    ax.legend(handles, phases, loc="upper right",
              title="Phase", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    return fig, ax


def print_phase_summary(gantt_df):
    """Mean / min / max duration per phase (hours)."""
    summary = gantt_df.groupby("phase")["duration_h"].agg(
        ["mean", "min", "max"]).round(1)
    print("Duration per phase (hours):")
    print(summary)
    print()


def print_per_turbine_total(gantt_df):
    """Throughput time per turbine and total project duration."""
    per_turbine = gantt_df.groupby("turbine_id").agg(
        eerste_start=("start", "min"),
        laatste_stop=("stop", "max"),
    ).reset_index()
    per_turbine["doorlooptijd_d"] = (
        per_turbine["laatste_stop"] - per_turbine["eerste_start"]
    ).dt.total_seconds() / 86400

    print("Throughput time per turbine (days):")
    print(per_turbine[["turbine_id", "doorlooptijd_d"]].round(0).to_string(index=False))
    total = (per_turbine["laatste_stop"].max()
             - per_turbine["eerste_start"].min()).days
    print(f"\nTotal project: {total} days\n")


def print_per_turbine_phase(gantt_df):
    """Duration per phase per turbine (days)."""
    per_turbine = (gantt_df.groupby(["turbine_id", "phase"])["duration_h"]
                   .sum().unstack(fill_value=0) / 24).round(1)
    per_turbine["TOTAL"] = per_turbine.sum(axis=1)
    print("Duration per phase per turbine (days):")
    print(per_turbine.T)
    print()


def run_analysis(result, show_plots=True):
    gantt_df, anchors_df = build_turbine_tracking_df(result)

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Turbines with data: {gantt_df['turbine_id'].nunique()}\n")

    print_phase_summary(gantt_df)
    print_per_turbine_total(gantt_df)
    print_per_turbine_phase(gantt_df)

    fig, ax = plot_turbine_gantt(gantt_df)
    if show_plots:
        plt.show()

    return gantt_df, anchors_df


def print_tte_debug(result):
    """Per turbine: CLV queueing, TT&E and WTG shifts, active and total hours."""
    gantt_df, _ = build_turbine_tracking_df(result)
    g = gantt_df.set_index(["turbine_id", "phase"])

    print("=" * 78)
    print("TT&E and WTG commissioning per turbine")
    print("=" * 78)
    print(f"{'Turbine':>7} {'CLV queue h':>11} {'TTE shifts':>10} {'TTE active h':>12} "
          f"{'TTE total h':>11} {'WTG shifts':>10} {'WTG active h':>12}")
    print("-" * 78)

    def val(tid, phase, col):
        try:
            v = g.loc[(tid, phase), col]
            return 0 if pd.isna(v) else v
        except KeyError:
            return 0

    for tid in sorted(gantt_df["turbine_id"].unique()):
        print(f"{tid:>7} {val(tid, 'Waiting for CLV', 'duration_h'):>11.1f} "
              f"{int(val(tid, 'TT&E', 'n_shifts')):>10} "
              f"{val(tid, 'TT&E', 'active_h'):>12.1f} "
              f"{val(tid, 'TT&E', 'duration_h'):>11.1f} "
              f"{int(val(tid, 'Hot commissioning', 'n_shifts')):>10} "
              f"{val(tid, 'Hot commissioning', 'active_h'):>12.1f}")
    print()


def compare_start_dates(start_dates=None, run_simulation=None, show_plots=True):
    """Run the active scenario for several start dates and compare durations."""
    if run_simulation is None:
        raise ValueError(
            "Pass run_simulation: "
            "compare_start_dates(run_simulation=run_simulation)"
        )
    if start_dates is None:
        start_dates = cfg.START_DATES

    rows = []
    results = {}

    for sd in start_dates:
        label = sd.strftime("%Y-%m-%d")
        print("=" * 60)
        print(f"RUN, start date {label}")
        print("=" * 60)

        result = run_simulation(verbose=True, start_date=sd)
        gantt_df, _ = build_turbine_tracking_df(result)
        results[label] = (result, gantt_df)

        per_turbine = gantt_df.groupby("turbine_id").agg(
            eerste_start=("start", "min"),
            laatste_stop=("stop", "max"),
        )
        project_dagen = (per_turbine["laatste_stop"].max()
                         - per_turbine["eerste_start"].min()).total_seconds() / 86400
        gem_doorloop = ((per_turbine["laatste_stop"]
                         - per_turbine["eerste_start"]).dt.total_seconds()
                        / 86400).mean()

        rows.append({
            "startdatum": label,
            "totale_duur_d": round(result.duration_days, 1),
            "projectduur_d": round(project_dagen, 1),
            "gem_doorlooptijd_d": round(gem_doorloop, 1),
            "duur_per_turbine_d": round(result.duration_days / cfg.N_TARGET, 1),
        })

    compare_df = pd.DataFrame(rows)

    print("\n" + "=" * 60)
    print("START DATE COMPARISON")
    print("=" * 60)
    print(compare_df.to_string(index=False))
    print()

    if show_plots:
        _plot_start_date_comparison(compare_df, results)

    return compare_df, results


def _plot_start_date_comparison(compare_df, results):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.bar(compare_df["startdatum"], compare_df["projectduur_d"],
            color="#185FA5", edgecolor="black")
    ax1.set_ylabel("Project duration (days)")
    ax1.set_xlabel("Start date")
    ax1.set_title("Project duration per start date")
    ax1.grid(axis="y", alpha=0.3)
    for i, v in enumerate(compare_df["projectduur_d"]):
        ax1.text(i, v, f"{v:.0f}", ha="center", va="bottom", fontsize=9)

    for label, (result, gantt_df) in results.items():
        per_turbine = gantt_df.groupby("turbine_id").agg(
            eerste_start=("start", "min"),
            laatste_stop=("stop", "max"),
        )
        doorloop = ((per_turbine["laatste_stop"]
                     - per_turbine["eerste_start"]).dt.total_seconds() / 86400)
        ax2.plot(per_turbine.index, doorloop, marker="o",
                 markersize=3, label=label)

    ax2.set_xlabel("Turbine")
    ax2.set_ylabel("Throughput time (days)")
    ax2.set_title("Throughput time per turbine")
    ax2.legend(title="Start date", fontsize=8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()
