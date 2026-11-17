"""Run one simulation (config.SCENARIO from config.SIMULATION_START) and show the results.

    python main.py
    python main.py --scenario "500,10,100" --start 2017-07-01 --no-plots
"""

import argparse
import datetime as dt

import config as cfg
from simulation import run_simulation
from analysis import run_analysis


def main(show_plots=True):
    print("=" * 60)
    print("FOWT INSTALLATION CHAIN, OpenCLSim simulation")
    print("=" * 60)
    print()

    result = run_simulation(verbose=True)
    gantt_df, anchors_df = run_analysis(result, show_plots=show_plots)

    return result, gantt_df, anchors_df


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Run one FOWT installation simulation.")
    p.add_argument("--scenario", help='key in config.LOCATION_SCENARIOS, e.g. "100,10,100"')
    p.add_argument("--start", help="start date YYYY-MM-DD (UTC)")
    p.add_argument("--no-plots", action="store_true")
    a = p.parse_args()
    if a.scenario:
        cfg.SCENARIO = a.scenario
    if a.start:
        cfg.SIMULATION_START = dt.datetime.fromisoformat(a.start).replace(
            tzinfo=dt.timezone.utc)
    main(show_plots=not a.no_plots)
