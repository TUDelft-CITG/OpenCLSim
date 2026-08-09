

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import openclsim.model as model

import config as cfg


def get_activity_log(activity):
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
    for sub in model.get_subprocesses(repeat_act):
        if name_contains.lower() in sub.name.lower():
            return sub
    raise ValueError(f"Sub-activity niet gevonden: {name_contains}")


def find_all_subs(repeat_act, name_contains):
    matches = [sub for sub in model.get_subprocesses(repeat_act)
               if name_contains.lower() in sub.name.lower()]
    if not matches:
        raise ValueError(f"Sub-activity niet gevonden: {name_contains}")
    return matches


def merged_leg_log(activity_list, name_contains):
    frames = []
    for act in activity_list:
        sub = find_sub(act, name_contains)
        frames.append(get_activity_log(sub))
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("start").reset_index(drop=True)
    return merged

def build_turbine_tracking_df(result):
    act = result.activities
    n_turbines = cfg.N_TARGET

    anchor_times = {
        # Productie
        "production_work":
            get_activity_log(find_sub(act["production_activity"], "manufacturing floater")),
        "production_done":
            get_activity_log(find_sub(act["production_activity"], "floater into stockyard")),
        # Launch
        "launch_start":
            get_activity_log(find_sub(act["launch_activity"], "[WW] launching 1 floater")),
        "launched":
            get_activity_log(find_sub(act["launch_activity"], "floater 1 into water")),
        "at_ws1":
            get_activity_log(find_sub(act["launch_activity"], "floater into wet storage 1")),
        # Floater carrier leg (post_launch → WS2); WS1 + post_launch staging
        # vallen samen in de 'Buffer berth 1'-fase (at_ws1_stop -> loaded_start).
        "loaded_at_berth":
            merged_leg_log(act["floater_leg_activities"], "loading 1 floater from launch berth"),
        "at_wet_storage":
            merged_leg_log(act["floater_leg_activities"], "delivering floater at wet storage"),
        # Tug leg (WS2 → Integration)
        "tug_pickup":
            merged_leg_log(act["tug_leg_activities"], "tug picks up floater from wet storage"),
        "at_integration":
            merged_leg_log(act["tug_leg_activities"], "tug delivers floater at berth IP1"),
        # Integratie A (intake nu vanaf pre_integration; IP1 + pre_integration
        # staging vallen samen in de 'Buffer berth 2'-fase).
        "assembly_intake":
            get_activity_log(find_sub(act["assembly_activity_A"], "move floater from pre-integration to integration quay")),
        "assembly_handover":
            get_activity_log(find_sub(act["assembly_activity_A"], "handover to mid-buffer")),
        # Commissioning B
        "commissioning_intake":
            get_activity_log(find_sub(act["assembly_activity_B"], "intake from mid-buffer")),
        "commissioning_work":
            get_activity_log(find_sub(act["assembly_activity_B"], "commissioning & testing")),
        "at_ws3":
            get_activity_log(find_sub(act["assembly_activity_B"], "release commissioned turbine to wet storage 3")),
        # Turbine carrier leg (WS3 → Site)
        "tc_loaded":
            merged_leg_log(act["turbine_leg_activities"], "[SE]loading integrated turbine"),
        "tc_offloaded":
            merged_leg_log(act["turbine_leg_activities"], "[SE]offloading turbine at site"),
        # Installatie op site
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

    # Zorg dat alle datetime kolommen in anchors_df timezone-aware zijn (UTC)
    for col in anchors_df.columns:
        if col.endswith("_start") or col.endswith("_stop"):
            if anchors_df[col].dtype.kind == "M":  # datetime kolom
                if anchors_df[col].dt.tz is None:
                    anchors_df[col] = anchors_df[col].dt.tz_localize("UTC")


    sites = getattr(result, "sites", {}) or {}
    mf_bypassed = sites.get("wet_storage_1", "x") is None     # Buffer berth 1
    ip1_bypassed = sites.get("berth_ip1", "x") is None        # Buffer berth 2
    ip2_bypassed = sites.get("wet_storage_3", "x") is None    # Buffer berth 3

    floatoff_stop = "loaded_at_berth_start" if mf_bypassed else "at_ws1_stop"
    tow_to_ip_stop = "assembly_intake_start" if ip1_bypassed else "at_integration_stop"
    comm_stop = "tc_loaded_start" if ip2_bypassed else "at_ws3_stop"

    phase_defs = [
        ("Produced floater in stockyard",   "production_work_start",      "launched_start"),
        ("Float-off",                       "launched_start",             floatoff_stop),
    ]
    if not mf_bypassed:
        phase_defs.append(
            ("Buffer berth 1",              "at_ws1_stop",                "loaded_at_berth_start"))
    phase_defs += [
        ("Tow floater to wet storage",      "loaded_at_berth_start",      "at_wet_storage_start"),
        ("Wet storage",                     "at_wet_storage_start",        "tug_pickup_start"),
        ("Tow floater to integration port", "tug_pickup_start",           tow_to_ip_stop),
    ]
    if not ip1_bypassed:
        phase_defs.append(
            ("Buffer berth 2",              "at_integration_stop",        "assembly_intake_start"))
    phase_defs += [
        ("Turbine integration & WTG assembly", "assembly_intake_start",   "commissioning_intake_start"),
        ("Cold commissioning",         "commissioning_intake_start", comm_stop),
    ]
    if not ip2_bypassed:
        phase_defs.append(
            ("Buffer berth 3",              "at_ws3_stop",                "tc_loaded_start"))
    phase_defs += [
        ("Tow-out to project site",         "tc_loaded_start",           "tc_offloaded_stop"),
  
        ("Mooring hookup",                  "tc_offloaded_stop",         "installed1_stop"),

        ("IAC hookup",                      "installed1_stop",           "installed2_stop"),
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
    tte_shift = find_sub(act["stringing_activity"], "[SE]TTE at site")
    wtg_shift = find_sub(act["stringing_activity"], "[SE]WTG commissioning at site")
    tte_log = get_activity_log(tte_shift)
    wtg_log = get_activity_log(wtg_shift)

    # Zorg dat tte_log en wtg_log timezone-aware zijn
    for col in ["start", "stop"]:
        if col in tte_log.columns and len(tte_log) > 0:
            if tte_log[col].dt.tz is None:
                tte_log[col] = tte_log[col].dt.tz_localize("UTC")
        if col in wtg_log.columns and len(wtg_log) > 0:
            if wtg_log[col].dt.tz is None:
                wtg_log[col] = wtg_log[col].dt.tz_localize("UTC")

    def _make_utc(ts):
        if pd.isna(ts):
            return ts
        ts = pd.Timestamp(ts)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    iac_stops = {}
    for tid in range(1, n_turbines + 1):
        iac_row = anchors_df.loc[anchors_df["turbine_id"] == tid]
        raw = iac_row["installed2_stop"].iloc[0] if len(iac_row) else pd.NaT
        iac_stops[tid] = _make_utc(raw)

    # Sorteer turbines op iac_stop om grenzen te bepalen
    sorted_tids = sorted(
        [tid for tid in iac_stops if pd.notna(iac_stops[tid])],
        key=lambda t: iac_stops[t]
    )

    for i, tid in enumerate(sorted_tids):
        iac_stop = iac_stops[tid]
        if i + 1 < len(sorted_tids):
            next_iac = iac_stops[sorted_tids[i + 1]]
        else:
            next_iac = pd.Timestamp("2100-01-01", tz="UTC")

        # Filter TT&E shifts: exact N_TTE_SHIFTS shifts per turbine
        # die beginnen na iac_stop van deze turbine
        N_TTE_SHIFTS = getattr(cfg, "N_TTE_SHIFTS", 18)
        N_WTG_SHIFTS = getattr(cfg, "N_WTG_SHIFTS", 18)

        tte_candidates = tte_log[
            tte_log["start"] >= iac_stop
        ].sort_values("start").reset_index(drop=True)
        tte_turbine = tte_candidates.head(N_TTE_SHIFTS)

        tte_stop = pd.NaT
        if len(tte_turbine) > 0:
            tte_start = iac_stop
            tte_stop = tte_turbine["stop"].max()
            tte_active_h = ((tte_turbine["stop"] - tte_turbine["start"])
                            .dt.total_seconds() / 3600).sum()

            if pd.notna(tte_start) and pd.notna(tte_stop) and tte_stop > tte_start:
                rows.append({
                    "turbine_id": tid,
                    "phase": "TT&E",
                    "start": tte_start,
                    "stop": tte_stop,
                    "duration_h": (tte_stop - tte_start).total_seconds() / 3600,
                    "active_h": tte_active_h,
                    "n_shifts": len(tte_turbine),
                })

        # Filter WTG shifts: exact N_WTG_SHIFTS shifts na laatste TT&E shift
        wtg_search_start = tte_stop if pd.notna(tte_stop) else iac_stop
        wtg_candidates = wtg_log[
            wtg_log["start"] >= wtg_search_start
        ].sort_values("start").reset_index(drop=True)
        wtg_turbine = wtg_candidates.head(N_WTG_SHIFTS)

        if len(wtg_turbine) > 0:
            wtg_start = wtg_search_start
            wtg_stop = wtg_turbine["stop"].max()
            wtg_active_h = ((wtg_turbine["stop"] - wtg_turbine["start"])
                            .dt.total_seconds() / 3600).sum()

            if pd.notna(wtg_start) and pd.notna(wtg_stop) and wtg_stop > wtg_start:
                rows.append({
                    "turbine_id": tid,
                    "phase": "Hot commissioning",
                    "start": wtg_start,
                    "stop": wtg_stop,
                    "duration_h": (wtg_stop - wtg_start).total_seconds() / 3600,
                    "active_h": wtg_active_h,
                    "n_shifts": len(wtg_turbine),
                })

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
    "Cold commissioning":                   "#ff6565",
    "Buffer berth 3":                            "#f7afaf",
    "Tow-out to project site":                   "#36b736",
    "Mooring hookup":                            "#bdaa00a8",
    "IAC hookup":                                "#ffe600",
    "TT&E":                                      "#fced6b",
    "Hot commissioning":                         "#fffaa0",
}

_PHASE_ORDER = list(_PHASE_COLORS.keys())


def plot_turbine_gantt(df, turbine_ids=None, figsize=(14, 10)):
    """Tekent een Gantt-chart per turbine."""
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
    ax.set_xlabel("Tijd")
    
    total_days = (df["stop"].max() - df["start"].min()).total_seconds() / 86400
    ax.set_title(f"Gantt-chart per turbine (N={len(turbine_ids)}) — "
                 f"totale duur {total_days:.0f} d ({total_days / 365:.2f} jaar)")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="x", alpha=0.3)

    handles = [plt.Rectangle((0, 0), 1, 1, color=_PHASE_COLORS[p]) for p in phases]

    ax.legend(handles, phases, loc="upper right",
              title="Fase", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    return fig, ax


def print_phase_summary(gantt_df):
    """Gemiddelde / min / max duur per fase (in uren)."""
    summary = gantt_df.groupby("phase")["duration_h"].agg(
        ["mean", "min", "max"]).round(1)
    print("Gemiddelde duur per fase (uren):")
    print(summary)
    print()


def print_per_turbine_total(gantt_df):
    """Doorlooptijd per turbine + totale projectduur."""
    per_turbine = gantt_df.groupby("turbine_id").agg(
        eerste_start=("start", "min"),
        laatste_stop=("stop", "max"),
    ).reset_index()
    per_turbine["doorlooptijd_d"] = (
        per_turbine["laatste_stop"] - per_turbine["eerste_start"]
    ).dt.total_seconds() / 86400

    print("Doorlooptijd per turbine (dagen):")
    print(per_turbine[["turbine_id", "doorlooptijd_d"]].round(0).to_string(index=False))
    totaal = (per_turbine["laatste_stop"].max()
              - per_turbine["eerste_start"].min()).days
    print(f"\nTotaal project: {totaal} dagen\n")


def print_per_turbine_phase(gantt_df):
    """Duur per fase per turbine (in dagen)."""
    per_turbine = (gantt_df.groupby(["turbine_id", "phase"])["duration_h"]
                   .sum().unstack(fill_value=0) / 24).round(1)
    per_turbine["TOTAAL"] = per_turbine.sum(axis=1)
    print("Duur per fase per turbine (in dagen):")
    print(per_turbine.T)
    print()

def run_analysis(result, show_plots=True):
    gantt_df, anchors_df = build_turbine_tracking_df(result)

    print("=" * 60)
    print("RESULTATEN")
    print("=" * 60)
    print(f"Aantal turbines met data: {gantt_df['turbine_id'].nunique()}\n")

    print_phase_summary(gantt_df)
    print_per_turbine_total(gantt_df)
    print_per_turbine_phase(gantt_df)

    fig, ax = plot_turbine_gantt(gantt_df)
    if show_plots:
        plt.show()

    return gantt_df, anchors_df

def print_tte_debug(result):
    """
    Print per turbine: aantal shifts, actieve uren, wachttijd TT&E en WTG.
    Gebruik dit om te controleren of shifts correct worden toegewezen.
    """
    act = result.activities
    tte_shift = find_sub(act["stringing_activity"], "[SE]TTE at site")
    wtg_shift = find_sub(act["stringing_activity"], "[SE]WTG commissioning at site")
    tte_log = get_activity_log(tte_shift)
    wtg_log = get_activity_log(wtg_shift)

    # voeg duration_h toe
    tte_log["duration_h"] = (tte_log["stop"] - tte_log["start"]).dt.total_seconds() / 3600
    wtg_log["duration_h"] = (wtg_log["stop"] - wtg_log["start"]).dt.total_seconds() / 3600

    print("=" * 70)
    print("DEBUG: TT&E en WTG commissioning shifts per turbine")
    print("=" * 70)
    print(f"{'Turbine':>8} {'TTE shifts':>10} {'TTE actief h':>13} "
          f"{'TTE wacht h':>12} {'WTG shifts':>10} {'WTG actief h':>13}")
    print("-" * 70)

    gantt_df, anchors_df = build_turbine_tracking_df(result)

    iac_stops = {}
    n_turbines = cfg.N_TARGET
    for tid in range(1, n_turbines + 1):
        iac_row = anchors_df.loc[anchors_df["turbine_id"] == tid]
        iac_stops[tid] = (iac_row["installed2_stop"].iloc[0]
                          if len(iac_row) else pd.NaT)

    sorted_tids = sorted(
        [t for t in iac_stops if pd.notna(iac_stops[t])],
        key=lambda t: iac_stops[t]
    )

    for i, tid in enumerate(sorted_tids):
        iac_stop = iac_stops[tid]
        next_iac = (iac_stops[sorted_tids[i + 1]]
                    if i + 1 < len(sorted_tids)
                    else pd.Timestamp("2100-01-01", tz="UTC"))

        tte_t = tte_log[(tte_log["start"] >= iac_stop) &
                        (tte_log["start"] < next_iac)]
        tte_active = tte_t["duration_h"].sum()
        tte_total = ((tte_t["stop"].max() - iac_stop).total_seconds() / 3600
                     if len(tte_t) else 0)
        tte_wacht = tte_total - tte_active

        tte_stop = tte_t["stop"].max() if len(tte_t) else iac_stop
        wtg_t = wtg_log[(wtg_log["start"] >= tte_stop) &
                        (wtg_log["start"] < next_iac)]
        wtg_active = wtg_t["duration_h"].sum()

        print(f"{tid:>8} {len(tte_t):>10} {tte_active:>13.1f} "
              f"{tte_wacht:>12.1f} {len(wtg_t):>10} {wtg_active:>13.1f}")

    print("-" * 70)
    print(f"Totaal TT&E shifts: {len(tte_log)} | "
          f"Totaal WTG shifts: {len(wtg_log)}")
    print(f"Verwacht per turbine: "
          f"{len(tte_log) // n_turbines} TT&E, "
          f"{len(wtg_log) // n_turbines} WTG")
    print()


def compare_start_dates(start_dates=None, run_simulation=None, show_plots=True):
    if run_simulation is None:
        raise ValueError(
            "Geef run_simulation mee: "
            "compare_start_dates(run_simulation=run_simulation)"
        )
    if start_dates is None:
        start_dates = cfg.START_DATES

    rows = []
    results = {}

    for sd in start_dates:
        label = sd.strftime("%Y-%m-%d")
        print("=" * 60)
        print(f"RUN — startdatum {label}")
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
    print("VERGELIJKING STARTDATA")
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
    ax1.set_ylabel("Projectduur (dagen)")
    ax1.set_xlabel("Startdatum")
    ax1.set_title("Projectduur per startdatum")
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
    ax2.set_ylabel("Doorlooptijd (dagen)")
    ax2.set_title("Doorlooptijd per turbine")
    ax2.legend(title="Startdatum", fontsize=8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

