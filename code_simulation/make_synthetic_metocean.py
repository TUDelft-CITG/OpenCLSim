"""Write a synthetic metocean file in the format simulation.py expects.

For testing the code without the ERA5 data set. Results obtained with these
files have no physical meaning.

    python tools/make_synthetic_metocean.py calm   data/metocean_calm.xlsx
    python tools/make_synthetic_metocean.py random data/metocean_random.xlsx

calm    every violation flag is 0 (no weather downtime)
random  seasonal AR(1) signal with one arbitrary limit per criterion
"""

import sys

import numpy as np
import pandas as pd

VIOL_COLS = {
    "viol_launching":            2.5,
    "viol_sailing_LtoWS":        2.0,
    "viol_sailing_WStoIP":       2.5,
    "viol_tower_assembly":       3.0,
    "viol_integration":          2.2,
    "viol_assembly_nac":         2.0,
    "viol_assembly_blades":      1.8,
    "viol_sailing_IPtoSite":     2.0,
    "viol_installation":         1.8,
    "viol_IAChookup":            2.0,
    "viol_TTE":                  2.2,
    "viol_WTGcommissionning":    2.2,
}


def build(mode, start="2016-12-01", stop="2021-12-31", seed=1):
    t = pd.date_range(start, stop, freq="h", tz="UTC")
    df = pd.DataFrame(index=t)
    df.index.name = "Time"
    df["ts"] = t.asi8 / 1e9
    if mode == "calm":
        for c in VIOL_COLS:
            df[c] = 0
    elif mode == "random":
        rng = np.random.default_rng(seed)
        doy = t.dayofyear.values
        seasonal = 1.6 + 0.8 * np.cos(2 * np.pi * (doy - 15) / 365.25)
        x = np.zeros(len(t))
        eps = rng.normal(0, 0.12, len(t))
        for i in range(1, len(t)):
            x[i] = 0.985 * x[i - 1] + eps[i]
        signal = np.clip(seasonal + x, 0.1, None)
        for c, limit in VIOL_COLS.items():
            df[c] = (signal > limit).astype(int)
    else:
        raise ValueError("mode must be 'calm' or 'random'")
    df.index = df.index.tz_localize(None)
    return df


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    build(mode).to_excel(out)
    print(f"written {out}")
