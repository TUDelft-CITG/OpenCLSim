"""Combine the batch results of many runs into one Excel file.

Reads the ``resultaten_*.xlsx`` file in every run folder of a batch output
folder (as written by run_batch.py) and writes ``alle_resultaten_gecombineerd.xlsx``
with two sheets:

    resultaten  the 'samenvatting' sheets of all runs
    gantt_data  the 'gantt_data' sheets of all runs

Both start with the column ``simulatie`` (the run folder name) and the
parameter columns in PARAM_COLUMNS. Parameter values are parsed from the run
folder name, so the batch label (``run_batch.py --label``) must follow one of
these patterns; parameters that do not occur in a name stay empty:

    distances          "... d1_100km, d2_10km, d3_0km ..."  or  "I8_0,10,100 ..."
    buffer berth 1     "... 2 spots berth 1 ..."            or  "..._SpotBB_1"
    wet storage        "... 50 spots WS ..."
    production rate    "... production rate 1 unit 14.60 day ..."
    vessel speeds      "... Vessel Speed loaded 3 ...", "... Vessel Speed empty 12 ..."
    weather limit      "... 1.2 weather conditions ..."
    weather window     "... 2 weather window length ..."
    metocean year      "..., 2015_<date>_<time>"
    vessels per leg    "... number of vessels per leg 3 ..."

Usage:

    python combine_results.py [BATCH_DIR] [OUTPUT_XLSX]

BATCH_DIR defaults to ``batch_output``; OUTPUT_XLSX defaults to
``BATCH_DIR/alle_resultaten_gecombineerd.xlsx``.
"""

import re
import sys
from pathlib import Path

import pandas as pd

BATCH_DIR_DEFAULT = "batch_output"
OUTPUT_NAME_DEFAULT = "alle_resultaten_gecombineerd.xlsx"

PARAM_COLUMNS = [
    "d1_km", "d2_km", "d3_km",
    "v_loaded", "v_unloaded",
    "WW_duration", "WW_limit", "WW_year",
    "N_BB1", "N_BB2", "N_BB3", "N_WS", "N_AHT",
    "production_rate_d_per_unit",
]

DIST_PATTERN = re.compile(
    r"d1_(?P<d1>\d+(?:\.\d+)?)km.*?"
    r"d2_(?P<d2>\d+(?:\.\d+)?)km.*?"
    r"d3_(?P<d3>\d+(?:\.\d+)?)km",
    re.IGNORECASE,
)

PROD_RATE_PATTERN = re.compile(
    r"production rate\s+\d+(?:\.\d+)?\s*units?\s+"
    r"(?P<rate>\d+(?:\.\d+)?)\s*day",
    re.IGNORECASE,
)

VESSEL_SPEED_LOADED_PATTERN = re.compile(
    r"Vessel Speed loaded\s+(?P<v>\d+(?:\.\d+)?)", re.IGNORECASE
)
VESSEL_SPEED_EMPTY_PATTERN = re.compile(
    r"Vessel Speed empty\s+(?P<v>\d+(?:\.\d+)?)", re.IGNORECASE
)
WW_LIMIT_PATTERN = re.compile(
    r"(?P<v>\d+(?:\.\d+)?)\s+weather conditions", re.IGNORECASE
)
WW_DURATION_PATTERN = re.compile(
    r"(?P<v>\d+(?:\.\d+)?)\s+weather window length", re.IGNORECASE
)
SPOTS_BERTH_PATTERN = re.compile(
    r"(?P<v>\d+(?:\.\d+)?)\s+spots berth\s+(?P<berth>\d+)", re.IGNORECASE
)
SPOTS_WS_PATTERN = re.compile(
    r"(?P<v>\d+(?:\.\d+)?)\s+spots WS", re.IGNORECASE
)
VESSELS_PER_LEG_PATTERN = re.compile(
    r"number of vessels per leg\s+(?P<v>\d+(?:\.\d+)?)", re.IGNORECASE
)
WW_YEAR_PATTERN = re.compile(r",\s*(?P<year>20\d{2})_\d{8}_\d{6}")

COMPACT_DIST_PATTERN = re.compile(
    r"^I\d+_(?P<d1>\d+(?:\.\d+)?),(?P<d2>\d+(?:\.\d+)?),(?P<d3>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
COMPACT_SPOTBB_PATTERN = re.compile(r"_SpotBB_(?P<v>\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_distances(sim_name: str):
    """d1, d2, d3 (km) from a folder name, or (None, None, None)."""
    m = DIST_PATTERN.search(sim_name)
    if not m:
        return None, None, None
    return float(m["d1"]), float(m["d2"]), float(m["d3"])


def parse_production_rate(sim_name: str):
    """Production rate (days per unit) from a folder name, or None."""
    m = PROD_RATE_PATTERN.search(sim_name)
    if not m:
        return None
    return float(m["rate"])


def parse_sweep_params(sim_name: str) -> dict:
    """All parameters found in a folder name, keyed by PARAM_COLUMNS names."""
    values: dict = {}

    d1, d2, d3 = parse_distances(sim_name)
    if d1 is not None:
        values["d1_km"], values["d2_km"], values["d3_km"] = d1, d2, d3
    else:
        m = COMPACT_DIST_PATTERN.search(sim_name)
        if m:
            values["d1_km"] = float(m["d1"])
            values["d2_km"] = float(m["d2"])
            values["d3_km"] = float(m["d3"])

    rate = parse_production_rate(sim_name)
    if rate is not None:
        values["production_rate_d_per_unit"] = rate

    m = VESSEL_SPEED_LOADED_PATTERN.search(sim_name)
    if m:
        values["v_loaded"] = float(m["v"])

    m = VESSEL_SPEED_EMPTY_PATTERN.search(sim_name)
    if m:
        values["v_unloaded"] = float(m["v"])

    m = WW_DURATION_PATTERN.search(sim_name)
    if m:
        values["WW_duration"] = float(m["v"])

    m = WW_LIMIT_PATTERN.search(sim_name)
    if m:
        values["WW_limit"] = float(m["v"])

    m = WW_YEAR_PATTERN.search(sim_name)
    if m:
        values["WW_year"] = int(m["year"])

    m = SPOTS_BERTH_PATTERN.search(sim_name)
    if m:
        values[f"N_BB{m['berth']}"] = float(m["v"])
    else:
        m = COMPACT_SPOTBB_PATTERN.search(sim_name)
        if m:
            values["N_BB1"] = float(m["v"])

    m = SPOTS_WS_PATTERN.search(sim_name)
    if m:
        values["N_WS"] = float(m["v"])

    m = VESSELS_PER_LEG_PATTERN.search(sim_name)
    if m:
        values["N_AHT"] = float(m["v"])

    return values


def find_result_files(batch_dir: Path):
    """(folder name, path) of the resultaten_*.xlsx file in every run folder."""
    files = []
    subdirs = sorted(p for p in batch_dir.iterdir() if p.is_dir())
    if not subdirs:
        raise FileNotFoundError(f"No run folders found in: {batch_dir}")

    for sub in subdirs:
        matches = sorted(sub.glob("resultaten_*.xlsx"))
        if not matches:
            print(f"  [skip] no resultaten_*.xlsx in: {sub.name}")
            continue
        if len(matches) > 1:
            print(f"  [note] several resultaten_*.xlsx in '{sub.name}', "
                  f"using: {matches[0].name}")
        files.append((sub.name, matches[0]))
    return files


def _with_prefix_columns(df: pd.DataFrame, sim_name: str,
                         sweep_params: dict) -> pd.DataFrame:
    """Prepend 'simulatie' and the parameter columns to df."""
    df = df.copy()
    df.insert(0, "simulatie", sim_name)
    for i, col in enumerate(PARAM_COLUMNS, start=1):
        df.insert(i, col, sweep_params.get(col))
    return df


def combine(batch_dir: Path, output_path: Path):
    print(f"Looking for runs in: {batch_dir.resolve()}\n")
    run_files = find_result_files(batch_dir)
    if not run_files:
        raise FileNotFoundError(
            f"No resultaten_*.xlsx files found under: {batch_dir}"
        )

    resultaten_frames = []
    gantt_frames = []

    for sim_name, xlsx_path in run_files:
        sweep_params = parse_sweep_params(sim_name)
        if sweep_params:
            found = ", ".join(f"{k}={v}" for k, v in sweep_params.items())
        else:
            found = "(no parameter recognised in the folder name)"
        print(f"  reading: {sim_name}\n    -> {found}")

        try:
            samenvatting = pd.read_excel(xlsx_path, sheet_name="samenvatting")
        except ValueError:
            print(f"    [note] no 'samenvatting' sheet in {xlsx_path.name}")
            samenvatting = None

        try:
            gantt = pd.read_excel(xlsx_path, sheet_name="gantt_data")
        except ValueError:
            print(f"    [note] no 'gantt_data' sheet in {xlsx_path.name}")
            gantt = None

        if samenvatting is not None:
            resultaten_frames.append(
                _with_prefix_columns(samenvatting, sim_name, sweep_params))
        if gantt is not None:
            gantt_frames.append(
                _with_prefix_columns(gantt, sim_name, sweep_params))

    resultaten_df = (pd.concat(resultaten_frames, ignore_index=True)
                     if resultaten_frames else pd.DataFrame())
    gantt_df = (pd.concat(gantt_frames, ignore_index=True)
                if gantt_frames else pd.DataFrame())

    print(f"\nTotal: {len(run_files)} runs.")
    print(f"  'resultaten' : {len(resultaten_df)} rows")
    print(f"  'gantt_data' : {len(gantt_df)} rows")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        resultaten_df.to_excel(writer, sheet_name="resultaten", index=False)
        gantt_df.to_excel(writer, sheet_name="gantt_data", index=False)

    print(f"\nWritten to: {output_path.resolve()}")


if __name__ == "__main__":
    batch_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(BATCH_DIR_DEFAULT)
    output_path = (Path(sys.argv[2]) if len(sys.argv) > 2
                   else batch_dir / OUTPUT_NAME_DEFAULT)
    combine(batch_dir, output_path)
