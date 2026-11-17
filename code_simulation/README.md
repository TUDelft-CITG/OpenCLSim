# FOWT installation logistics model (OpenCLSim)

Discrete-event simulation of the installation chain of a floating offshore
wind farm, built on [OpenCLSim](https://github.com/TUDelft-CITG/OpenCLSim).
It computes the total installation time of a 25-turbine farm as a function of
the distances between the ports in the chain and the local weather.

This folder accompanies

> C.W. Covers (2026). *When Distance Becomes Delay.* MSc thesis, Delft
> University of Technology, in collaboration with Royal HaskoningDHV.
> TODO: repository link

> TODO: paper reference and DOI of the archived code version

## Model in short

Four nodes on one line: manufacturing port, wet storage, integration port and
project site. The distances between them are `d1` (manufacturing port to wet
storage), `d2` (wet storage to integration port) and `d3` (integration port to
site).

| Process | What happens | Resources |
|---|---|---|
| A, A2 | floater production (180 per year) and launch | production team |
| A3 | buffer berth 1 to the departure slot | shuttle |
| B | tow of the floater to wet storage | `N_VESSELS_PER_LEG` vessel sets |
| B2 | tow from wet storage to the integration port | `N_VESSELS_PER_LEG` vessel sets |
| C0b | buffer berth 2 to the integration quay | shuttle |
| C1 | top-part integration, nacelle and three blades | integration team |
| C2 | cold commissioning (24 h) | commissioning team |
| C3 | buffer berth 3 to the tow-out slot | shuttle |
| D | tow-out, mooring hook-up (40 h), IAC hook-up (12 h) | `N_VESSELS_PER_LEG` vessel sets |
| E | TT&E and hot commissioning, 18 + 18 shifts of 2 h per turbine | one CLV |

The run ends when the last turbine is commissioned; that moment defines the
total installation time (`total_installation_d`). All parameters are in
`config.py`.

## Contents

| File | Purpose |
|---|---|
| `config.py` | all parameters, port layouts (`LOCATION_SCENARIOS`) and the path to the metocean file |
| `simulation.py` | the model; `run_simulation(verbose, start_date)` |
| `analysis.py` | per-turbine Gantt reconstruction, phase statistics, plots |
| `run_batch.py` | one scenario for several start dates; Excel, CSV and PNG output |
| `combine_results.py` | merges the batch output of many runs into one Excel file |
| `main.py` | one run of the baseline with printed results and a Gantt chart |
| `diagnostics.py` | check whether every weather-gated start had a workable window |
| `openclsim_patches.py` | two run-time changes to OpenCLSim the model needs (see below) |
| `tools/make_synthetic_metocean.py` | synthetic metocean file for testing without ERA5 |
| `tests/test_baseline_calm.py` | smoke test with a deterministic reference result |
| `data/metocean_era5.xlsx` | hourly weather series with the workability flags (see below) |

## Parameters (config.py)

| Name | Value | Meaning |
|---|---|---|
| `SIMULATION_START` | 2017-01-01 UTC | start of a single run (`main.py`) |
| `START_DATES` | 10 dates | first day of every second month from January 2017; used by `analysis.compare_start_dates` |
| `METOCEAN_PATH` | `data/metocean_era5.xlsx` | weather file; the environment variable `FOWT_METOCEAN_PATH` overrides it |
| `METOCEAN_PATH_MF`, `_WS`, `_IP`, `_PS` | `None` | optional separate file for the manufacturing port, wet storage, integration port and site; `None` means `METOCEAN_PATH` |
| `SCENARIO` | `"100,10,100"` | port layout, a key of `LOCATION_SCENARIOS` |
| `N_TARGET` | 25 | turbines (and floaters) to install |
| `N_VESSELS_PER_LEG` | 2 | vessel sets on each of the three tow legs |
| `MANUFACTURING_CAPACITY` | 6 | stockyard slots for finished floaters |
| `BERTH_STORAGE_MF_CAPACITY` | 1 | buffer berth 1, manufacturing port (0 = no berth) |
| `WET_STORAGE_CAPACITY` | 100 | wet storage slots |
| `BERTH_STORAGE_IP1_CAPACITY` | 1 | buffer berth 2, integration port, before integration (0 = no berth) |
| `BERTH_STORAGE_IP2_CAPACITY` | 1 | buffer berth 3, integration port, after cold commissioning (0 = no berth) |
| `PRODUCTION_TIME` | 2.03 d | one floater per 2.03 days (180 per year) |
| `LAUNCH_TIME` | 4 h | launch (float-off) |
| `INTEGRATION_TIME` | 1 h | top-part integration |
| `ASSEMBLY_NC_TOT` | 2 h | nacelle, and each of the three blades |
| `COMMISSIONING_TESTING_TIME` | 24 h | cold commissioning at the quay |
| `INSTALLATION_TIME` | 40 h | mooring hook-up |
| `IAC_HOOKUP_TIME` | 12 h | inter-array cable hook-up |
| `SHIFTS_PER_TURBINE` | 18 | TT&E shifts, and hot-commissioning shifts, per turbine |
| `TTE_TIME`, `WTG_COMMISSIONING_TIME` | 2 h | duration of one shift |
| `LAUNCH_TIME_WW` | 0.5 h | minimum workable window before launch |
| `INTEGRATION_WW` | 2 h | idem, integration |
| `ASSEMBLY_NACELLE_WW`, `ASSEMBLY_BLADE_WW` | 4 h | idem, nacelle and blades |
| `INSTALLATION_TIME_WW`, `IAC_HOOKUP_TIME_WW` | 1 h | idem, mooring and IAC hook-up |
| `TTE_TIME_WW`, `WTG_COMMISSIONING_TIME_WW` | 0.5 h | idem, per shift |
| `KNOT_KMH` | 1.83 | km/h per knot used for all speeds (exact value 1.852) |
| `VESSEL_SPEED_EMPTY` | 12 kn | sailing empty |
| `VESSEL_SPEED_LOADED` | 3 kn | towing |
| `VESSEL_SPEED_CLV` | 30 kn | not used: the CLV stays at the site |
| `LOCATION_SCENARIOS` | | node coordinates per layout |

Tows have no window parameter: their window is the full loaded sailing time.
`config.scenario_distances_km(name)` gives the distances of a layout as the
model computes them.

## Installation

Tested with Python 3.13. From the root of this repository:

```bash
pip install -e .                                   # OpenCLSim at this commit
pip install -r code_simulation/requirements.txt
```

`requirements.txt` lists the package versions of the reference environment.

## Metocean data

`data/metocean_era5.xlsx` holds an hourly series for the Moray Firth from
2014-01-01 00:00 to 2024-12-31 23:00 UTC (29 February 2024 is missing). Columns:

* `Time` (index) and `ts`, the same moment in seconds since 1970-01-01 UTC
* `Hs` significant wave height (m), `Tp` peak wave period (s), `U10` wind
  speed at 10 m (m/s), `Vc` current speed (m/s)
* one flag per criterion: 1 when a limit is exceeded, otherwise 0

| Flag | Used by | Exceeded when |
|---|---|---|
| `viol_launching` | launch | U10 > 10 m/s |
| `viol_sailing_LtoWS` | tow manufacturing port to wet storage | Hs > 2.5 m or Tp > 8 s |
| `viol_sailing_WStoIP` | tow wet storage to integration port | Hs > 2.5 m or Tp > 8 s |
| `viol_integration` | top-part integration | U10 > 12 m/s |
| `viol_assembly_nac` | nacelle assembly | U10 > 12 m/s |
| `viol_assembly_blades` | blade assembly | U10 > 10 m/s |
| `viol_sailing_IPtoSite` | tow-out to the site | Hs > 2.5 m or Tp > 8 s or U10 > 15 m/s |
| `viol_installation` | mooring hook-up | Hs > 2.0 m or U10 > 15 m/s or Vc ≥ 0.5 m/s |
| `viol_IAChookup` | IAC hook-up | Hs > 2.0 m or U10 > 15 m/s or Vc ≥ 0.5 m/s |
| `viol_TTE` | TT&E shifts | Tp > 8 s or U10 > 10 m/s |
| `viol_WTGcommissionning` | hot commissioning shifts | Tp > 8 s or U10 > 10 m/s |

The limits in the last column reproduce every flag in the file exactly.
`viol_tower_assembly` (U10 > 12 m/s) is in the file but not used. A run
must end before the end of the series (see the `weather_check` sheet).

TODO: ERA5 grid point, the source of `Vc`, and the file with limits scaled by
1.2 that was used for the western site (Havbredey).

ERA5 is published by the Copernicus Climate Change Service under CC BY 4.0.
Cite Hersbach et al. (2018), *ERA5 hourly data on single levels from 1940 to
present*, Copernicus Climate Change Service (C3S) Climate Data Store (CDS),
doi:10.24381/cds.adbb2d47, and state: "Contains modified Copernicus Climate
Change Service data [year]. Neither the European Commission nor ECMWF is
responsible for any use that may be made of the Copernicus information or
data it contains."

To test the code on a synthetic series instead:

```bash
python code_simulation/tools/make_synthetic_metocean.py random code_simulation/data/synthetic.xlsx
FOWT_METOCEAN_PATH=code_simulation/data/synthetic.xlsx python code_simulation/main.py
```

## Running

```bash
cd code_simulation
python main.py                                        # baseline 100,10,100
python main.py --scenario "500,10,100" --start 2017-07-01 --no-plots
python run_batch.py --scenario "100,10,100" --label baseline
python run_batch.py --scenario "Hub west" --label CaseStudy_v1
```

`run_batch.py` uses six start dates in 2017 (the first of every second month)
unless `--start-year`, `--n-years`, `--starts-per-year` or `--start-month` say
otherwise. Scenario keys are `"d1,d2,d3"` in km or one of the case-study
layouts (`Hub east`, `Hub west`, `Large scale east`, `Large scale west`,
`Central integration east`, `Central integration west`). The Gantt charts
use days from the start date on the x-axis (`GANTT_XAS = "relatief"`); any
other value gives calendar dates.

```bash
python combine_results.py                      # all runs in batch_output/
python combine_results.py batch_output out.xlsx
```

`combine_results.py` writes `alle_resultaten_gecombineerd.xlsx` with the
sheets `resultaten` and `gantt_data` of all runs, preceded by the run folder
name (`simulatie`) and the parameters it reads from that name. The recognised
name patterns are listed at the top of the script.

### Output of run_batch.py

Sheet `samenvatting`, one row per start date:

| Column | Meaning |
|---|---|
| `startdatum`, `startmaand` | start date of the run |
| `scenario`, `n_turbines` | settings |
| `total_installation_d` | **KPI**: days from start until the last turbine is commissioned |
| `total_installation_jaar` | the same in years |
| `projectduur_d` | first to last bar of the Gantt chart (equals the KPI within one hour) |
| `gem_doorlooptijd_d` | mean time from production start to commissioning, per turbine |
| `duur_per_turbine_d` | KPI divided by the number of turbines |
| `zero_shift_events` | skipped shifts into a full container; must be 0 |
| `weather_no_window`, `weather_beyond_data` | weather-gated starts without a workable window; must be 0 |

Other sheets: `eindanalyse` (mean, min, max, spread, standard deviation, best
and worst start month), `gantt_data` (one row per turbine and phase; `start_dag`
and `stop_dag` in days from the start date), `fases_<date>` (mean, min and max
duration per phase) and `weather_check` (per weather-gated activity).

## Reproducing the results

1. One batch per scenario, with a label that encodes the parameters, e.g.
   `python run_batch.py --scenario "500,10,100" --label "I1_500,10,100"`.
2. `python combine_results.py` to merge all batches.
3. The figures (OFAT, two-factor interaction, Monte Carlo, case study) are
   made from `alle_resultaten_gecombineerd.xlsx` in separate analysis
   notebooks, which are not part of this folder.

## Modelling notes

* **Geometry.** All nodes lie on the parallel 57.65 N; only the distances
  matter. The model uses WGS84 geodesic distances, which deviate less than
  0.4 % from the nominal km in the scenario key.
* **Weather.** One metocean series is used for all nodes. A weather-gated
  activity starts only at a moment from which the series shows no exceedance
  during the required window. For tows the window equals the full loaded
  sailing time, so a tow is only started if it can be completed within the
  limits. For the other activities the windows in `config.py` apply; an
  activity that has started is not interrupted. The series is hourly, so
  windows shorter than an hour act as "workable at the start hour".
* **Speeds.** Knots are converted with 1.83 km/h per knot in all reported
  runs (exact: 1.852), so the effective speeds are 1.2 % lower than nominal.
* **Vessels.** Each vessel of a leg makes a fixed number of round trips
  (25 over 2 vessels: 13 and 12).
* **Reservations.** A carrier claims a wet-storage slot before it delivers,
  and a tug reserves a berth at the integration port before it leaves wet
  storage. Both use token containers (`ws2_*`, `ip1_*`), so a vessel never
  holds a floater while waiting for space; this prevents deadlocks.
* **Event order.** The order in which the processes are registered at the end
  of `run_simulation` decides which process goes first at equal times.
  Changing it can change results slightly.
* **Towers** are always available at the integration port.
* **Per-turbine timelines** are reconstructed first in, first out. The CLV
  commissions one turbine at a time; time between IAC hook-up and the start
  of TT&E is shown as the phase "Waiting for CLV".
* **OpenCLSim changes** (`openclsim_patches.py`): a weather criterion that is
  never exceeded is treated as always workable (OpenCLSim raises an error
  there), and a shift from an empty origin waits for content instead of
  raising an error. In addition, the workable windows are computed once per
  series and criterion instead of at every weather check (speed only). All
  are applied when `simulation.py` is imported.
* **OpenCLSim weather plugin.** When the series holds no workable window of
  the required length after the current time, or the run passes the end of
  the series, OpenCLSim starts the activity at once. The `weather_check`
  sheet counts such starts; the metocean series must cover every run with
  margin.
* **Deadlock guard.** A run that has not finished after 10 simulated years
  stops with an error (recorded as NaN in `run_batch.py`).

## Tests

```bash
pytest code_simulation/tests
```

Runs the baseline on an all-workable synthetic series and checks the
deterministic result (82.375 days: the single CLV needs 72 h per turbine and
is the bottleneck).

## Changes since the thesis version (commit 2d3da4f, 9 August 2026)

Simulation results are unchanged: on synthetic metocean series, eight
combinations of scenario and start date (including d1 = 1500 km and the
case-study layout Hub west) gave identical durations and identical Gantt data,
computed with the original analysis.py, before and after the changes.

* Metocean path is relative and configurable; the file is read once and cached.
* Number of turbines comes from `N_TARGET`; trips per vessel are computed for
  any `N_VESSELS_PER_LEG` (before: only 1 to 5 and 10, otherwise a crash).
* `SHIFTS_PER_TURBINE` moved to `config.py`; unused parameters and objects removed.
* The deadlock guard now stops the run (before: it printed a message and the
  run continued forever).
* `run_batch.py` imported modules that are not in the repository
  (`simulation_BB123`, `analysis_BB123`); it now imports `simulation` and
  `analysis` and has a command line interface.
* **Gantt fix** in `analysis.py`: TT&E and hot-commissioning shifts were
  assigned to a turbine as the first 18 shifts after its IAC hook-up. When
  turbines queue for the CLV those shifts belong to earlier turbines, so the
  bars ended too early (baseline without weather: last bar on day 61.3, run
  ends on day 82.4). Shifts are now assigned through the CLV's claim and
  release of each turbine. This changes `projectduur_d`,
  `gem_doorlooptijd_d`, the phase tables and the Gantt charts, not
  `total_installation_d`.
* `combine_results.py`: default folder `batch_output` instead of a local
  Windows path.
* Workable weather windows are cached: identical results, runs 10 to 20
  times faster (one run of the baseline on the ERA5 series: 13 s instead of
  4 min).
* New: `diagnostics.py`, `weather_check` sheet, `zero_shift_events`,
  synthetic metocean tool, smoke test, English comments and messages.
  Excel sheet and column names are unchanged.

## Licence

MIT, as OpenCLSim (see `LICENSE.txt` in the repository root).
