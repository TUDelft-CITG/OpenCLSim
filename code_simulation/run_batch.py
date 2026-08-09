import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")         
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

import config as cfg
from simulation_BB123 import run_simulation
from analysis_BB123 import (build_turbine_tracking_df, _PHASE_COLORS,                           _PHASE_ORDER)


LABEL = "CaseStudy_v1"
START_YEAR = 2017
N_YEARS = 1
STARTS_PER_YEAR = 6
START_MONTH = 1

GANTT_XAS = "relatief"

def make_start_dates():
    step_months = 12 // STARTS_PER_YEAR
    dates = []
    for yr in range(N_YEARS):
        for k in range(STARTS_PER_YEAR):
            month = START_MONTH + k * step_months
            dates.append(
                dt.datetime(START_YEAR + yr, month, 1,
                            tzinfo=dt.timezone.utc)
            )
    return dates


def summarize_run(result, gantt_df):
    per_turbine = gantt_df.groupby("turbine_id").agg(
        eerste_start=("start", "min"),
        laatste_stop=("stop", "max"),
    )
    project_dagen = (per_turbine["laatste_stop"].max()
                     - per_turbine["eerste_start"].min()).total_seconds() / 86400
    gem_doorloop = ((per_turbine["laatste_stop"]
                     - per_turbine["eerste_start"]).dt.total_seconds()
                    / 86400).mean()

    summary_row = {
        "startdatum":              result.start_date.strftime("%Y-%m-%d"),
        "startmaand":              result.start_date.strftime("%Y-%m"),
        "scenario":                cfg.SCENARIO,
        "n_turbines":              cfg.N_TARGET,
        "total_installation_d":    round(result.duration_days, 1),
        "total_installation_jaar": round(result.duration_days / 365, 2),
        "projectduur_d":           round(project_dagen, 1),
        "gem_doorlooptijd_d":      round(gem_doorloop, 1),
        "duur_per_turbine_d":      round(result.duration_days / cfg.N_TARGET, 1),
    }

    fase_tabel = (gantt_df.groupby("phase")["duration_h"]
                  .agg(["mean", "min", "max"]) / 24).round(2)
    fase_tabel = fase_tabel.rename(columns={
        "mean": "gem_duur_d", "min": "min_duur_d", "max": "max_duur_d"
    }).reset_index().rename(columns={"phase": "fase"})

    return summary_row, fase_tabel


def gantt_plot_data(gantt_df, start_date):
    
    t0 = start_date.timestamp()
    df = gantt_df.copy()

    df["start_dag"] = (df["start"].map(lambda s: s.timestamp()) - t0) / 86400
    df["duur_dag"]  = (df["stop"] - df["start"]).dt.total_seconds() / 86400
    df["stop_dag"]  = df["start_dag"] + df["duur_dag"]

    # absolute as: identiek aan plot_gantt_fixed (mdates.date2num)
    df["start_datenum"] = df["start"].map(mdates.date2num)
    df["stop_datenum"]  = df["stop"].map(mdates.date2num)

    cols = ["turbine_id", "phase", "start", "stop",
            "duration_h", "duur_dag", "start_dag", "stop_dag",
            "start_datenum", "stop_datenum"]
    cols = [c for c in cols if c in df.columns]
    return (df[cols]
            .sort_values(["turbine_id", "start_dag"])
            .reset_index(drop=True))


def plot_gantt_fixed(gantt_df, start_date, xlim, ylim, title):
    turbine_ids = sorted(gantt_df["turbine_id"].unique())
    phases = [p for p in _PHASE_ORDER if p in gantt_df["phase"].unique()]

    total_days = (gantt_df["stop"].max()
                  - gantt_df["start"].min()).total_seconds() / 86400

    fig, ax = plt.subplots(figsize=(14, 10))

    t0 = start_date.timestamp()
    for y, tid in enumerate(turbine_ids):
        sub = gantt_df[gantt_df["turbine_id"] == tid]
        for _, row in sub.iterrows():
            if GANTT_XAS == "relatief":
                # dagen vanaf start
                left = (row["start"].timestamp() - t0) / 86400
                width = (row["stop"] - row["start"]).total_seconds() / 86400
            else:
                left = mdates.date2num(row["start"])
                width = mdates.date2num(row["stop"]) - left
            ax.barh(y, width, left=left,
                    color=_PHASE_COLORS.get(row["phase"], "#888888"),
                    edgecolor="black", linewidth=0.2, height=0.7)
    ax.set_xlim(xlim)
    ax.set_ylim(-0.5, ylim - 0.5)
    ax.set_yticks(range(ylim))
    ax.set_yticklabels([f"Turbine {t + 1}" for t in range(ylim)])
    ax.invert_yaxis()

    if GANTT_XAS == "relatief":
        ax.set_xlabel("Days from start")
    else:
        ax.set_xlabel("Installation time")
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    ax.set_title(f"{title} — Total duration {total_days:.0f} d "
                 f"({total_days / 365:.2f} jaar)")
    ax.grid(axis="x", alpha=0.3)

    handles = [plt.Rectangle((0, 0), 1, 1, color=_PHASE_COLORS[p])
               for p in phases]
    ax.legend(handles, phases, loc="upper right",
              title="Fase", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    return fig, ax


def plot_eindanalyse(summary_df, out_path):
    df = summary_df.dropna(subset=["total_installation_d"]).copy()

    sd = pd.to_datetime(df["startdatum"])
    df["maand"] = sd.dt.month
    df["jaar"] = sd.dt.year

    maanden = sorted(df["maand"].unique())
    maand_namen = ["jan", "feb", "mrt", "apr", "mei", "jun",
                   "jul", "aug", "sep", "okt", "nov", "dec"]

    fig, ax = plt.subplots(figsize=(12, 6))

    jaren = sorted(df["jaar"].unique())
    cmap = plt.get_cmap("viridis", max(len(jaren), 1))
    for j, jaar in enumerate(jaren):
        sub = df[df["jaar"] == jaar]
        ax.scatter(sub["maand"], sub["total_installation_d"],
                   color=cmap(j), s=70, edgecolor="black", linewidth=0.5,
                   zorder=3, label=str(jaar))

    for m in maanden:
        vals = df.loc[df["maand"] == m, "total_installation_d"]
        if len(vals) >= 2:
            ax.vlines(m, vals.min(), vals.max(),
                      color="grey", linewidth=1, zorder=1)
        ax.scatter(m, vals.mean(), marker="_", s=400,
                   color="red", linewidth=2, zorder=2)

    gem = df["total_installation_d"].mean()
    ax.axhline(gem, color="red", linestyle="--", alpha=0.6,
               label=f"gemiddelde = {gem:.0f} d")

    ax.set_xticks(maanden)
    ax.set_xticklabels([maand_namen[m - 1] for m in maanden])
    ax.set_ylabel("Total installation time (dagen)")
    ax.set_xlabel("Startmaand")
    ax.set_title(f"Total installation time per startmaand "
                 f"(LABEL: {LABEL}, scenario {cfg.SCENARIO})")
    ax.legend(title="Jaar", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

def main():
    start_dates = make_start_dates()

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("batch_output_interaction_V3") / f"{LABEL}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    gantt_dir = out_dir / "gantt_charts"
    gantt_dir.mkdir(exist_ok=True)
    gantt_data_dir = out_dir / "gantt_data"
    gantt_data_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("BATCH-RUN — FOWT-installatieketen")
    print("=" * 60)
    print(f"Label        : {LABEL}")
    print(f"Scenario     : {cfg.SCENARIO}")
    print(f"N_TARGET     : {cfg.N_TARGET}")
    print(f"Aantal runs  : {len(start_dates)} "
          f"({N_YEARS} jaar x {STARTS_PER_YEAR} startdata)")
    print(f"Gantt x-as   : {GANTT_XAS}")
    print(f"Output-map   : {out_dir.resolve()}")
    print("=" * 60)
    print()

    summary_rows = []
    fase_tabellen = {}
    runs = []       
    for i, sd in enumerate(start_dates, start=1):
        label = sd.strftime("%Y-%m-%d")
        print(f"[{i:2d}/{len(start_dates)}] Run startdatum {label} ...")

        try:
            result = run_simulation(verbose=False, start_date=sd)
            gantt_df, _ = build_turbine_tracking_df(result)

            summary_row, fase_tabel = summarize_run(result, gantt_df)
            summary_rows.append(summary_row)
            fase_tabellen[label] = fase_tabel
            runs.append((label, sd, gantt_df))

            print(f"          total installation time = "
                  f"{summary_row['total_installation_d']:.1f} d")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"          [FOUT] {type(e).__name__}: {e}")
            summary_rows.append({
                "startdatum": label,
                "startmaand": sd.strftime("%Y-%m"),
                "scenario": cfg.SCENARIO,
                "n_turbines": cfg.N_TARGET,
                "total_installation_d": float("nan"),
            })

    summary_df = pd.DataFrame(summary_rows)

    ymax = max((g["turbine_id"].nunique() for _, _, g in runs), default=1)

    if GANTT_XAS == "relatief":
        max_days = 0.0
        for label, sd, g in runs:
            t0 = sd.timestamp()
            end = (g["stop"].max().timestamp() - t0) / 86400
            max_days = max(max_days, end)
        xlim = (0, max_days * 1.05)
    else:
        earliest = min(sd for _, sd, _ in runs)
        latest = max(g["stop"].max() for _, _, g in runs)
        xlim = (mdates.date2num(earliest), mdates.date2num(latest))


    print()
    print("Gantt-charts tekenen met vaste assen ...")
    alle_gantt_data = []
    for label, sd, gantt_df in runs:
        title = (f"Gantt — start {label} "
                 f"(scenario {cfg.SCENARIO}, N={cfg.N_TARGET})")
        fig, ax = plot_gantt_fixed(gantt_df, sd, xlim, ymax, title)
        png_path = gantt_dir / f"gantt_{label}.png"
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # exacte getallen achter de chart los opslaan
        gdata = gantt_plot_data(gantt_df, sd)
        gdata.insert(0, "startdatum", label)
        csv_path = gantt_data_dir / f"gantt_data_{label}.csv"
        gdata.to_csv(csv_path, index=False)
        alle_gantt_data.append(gdata)

        print(f"  {png_path.name}  +  {csv_path.name}")

    if alle_gantt_data:
        combined_gantt = pd.concat(alle_gantt_data, ignore_index=True)
        combined_gantt.to_csv(
            gantt_data_dir / "gantt_data_alle_runs.csv", index=False)
    else:
        combined_gantt = pd.DataFrame()


    eind_png = out_dir / "eindanalyse_total_installation_time.png"
    plot_eindanalyse(summary_df, eind_png)
    print(f"\nEindanalyse-grafiek: {eind_png.name}")


    excel_path = out_dir / f"resultaten_{LABEL}_{stamp}.xlsx"


    geldig = summary_df.dropna(subset=["total_installation_d"])
    tit = geldig["total_installation_d"]

    if len(geldig) > 1:
        beste_maand     = geldig.loc[tit.idxmin(), "startmaand"]
        slechtste_maand = geldig.loc[tit.idxmax(), "startmaand"]
        spreiding       = round(tit.max() - tit.min(), 1)
        std             = round(tit.std(), 1)
    else:
        beste_maand     = geldig["startmaand"].iloc[0] if len(geldig) == 1 else "n.v.t."
        slechtste_maand = beste_maand
        spreiding       = 0.0
        std             = 0.0

    eindanalyse = pd.DataFrame([
        {"statistiek": "aantal runs",           "waarde": len(geldig)},
        {"statistiek": "gemiddelde (d)",        "waarde": round(tit.mean(), 1)},
        {"statistiek": "minimum (d)",           "waarde": round(tit.min(), 1)},
        {"statistiek": "maximum (d)",           "waarde": round(tit.max(), 1)},
        {"statistiek": "spreiding max-min (d)", "waarde": spreiding},
        {"statistiek": "standaarddeviatie (d)", "waarde": std},
        {"statistiek": "beste startmaand",      "waarde": beste_maand},
        {"statistiek": "slechtste startmaand",  "waarde": slechtste_maand},
    ])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="samenvatting", index=False)
        eindanalyse.to_excel(writer, sheet_name="eindanalyse", index=False)
        if not combined_gantt.empty:
            gantt_excel = combined_gantt.copy()
            for col in gantt_excel.columns:
                if isinstance(gantt_excel[col].dtype, pd.DatetimeTZDtype):
                    gantt_excel[col] = gantt_excel[col].dt.tz_localize(None)
            gantt_excel.to_excel(
                writer, sheet_name="gantt_data", index=False)
        for label in fase_tabellen:
            safe = label.replace("-", "")
            fase_tabellen[label].to_excel(
                writer, sheet_name=f"fases_{safe}"[:31], index=False)


    print()
    print("=" * 60)
    print("KLAAR")
    print("=" * 60)
    print(f"Excel        : {excel_path.resolve()}")
    print(f"Gantt-charts : {gantt_dir.resolve()} ({len(runs)} png's)")
    print(f"Gantt-data   : {gantt_data_dir.resolve()} "
          f"({len(runs)} csv's + gantt_data_alle_runs.csv)")
    print(f"Eindanalyse  : {eind_png.resolve()}")
    print()
    print("Total installation time per startdatum:")
    cols = [c for c in ["startdatum", "total_installation_d",
                        "projectduur_d", "duur_per_turbine_d"]
            if c in summary_df.columns]
    print(summary_df[cols].to_string(index=False))
    print()
    print("Eindanalyse:")
    print(eindanalyse.to_string(index=False))

    return summary_df, eindanalyse, out_dir


if __name__ == "__main__":
    main()
