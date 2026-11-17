"""Discrete-event model of a floating offshore wind turbine (FOWT) installation chain.

Four nodes: manufacturing port -> wet storage -> integration port -> project
site (distances d1, d2, d3; see config.LOCATION_SCENARIOS). Built on
OpenCLSim; the processes are

    A   floater production and launch (manufacturing port)
    A3  staging: buffer berth 1 -> launch-berth departure slot
    B   floater tow to wet storage           (N_VESSELS_PER_LEG carriers)
    B2  tow from wet storage to integration  (N_VESSELS_PER_LEG tugs)
    C0  tower supply (towers are always available)
    C0b staging: buffer berth 2 -> pre-integration slot
    C1  integration and WTG assembly (one team, weather-gated steps)
    C2  cold commissioning (one team)
    C3  staging: buffer berth 3 -> tow-out slot
    D   tow-out, mooring hook-up and IAC hook-up (N_VESSELS_PER_LEG carriers)
    E   TT&E and hot (WTG) commissioning by one CLV, in weather-gated shifts

Weather gating: a "[WW]" activity waits until the metocean series has a
workable window of the required length. For tows the window equals the full
sailing time, so a tow only departs if it can be completed without exceeding
the limit. The series is hourly, so windows are effectively whole hours.

Turbines are anonymous container units; analysis.py reconstructs per-turbine
timelines afterwards (first in, first out).

Run the baseline with ``python main.py``; batch runs with ``run_batch.py``.
"""

import datetime as dt
import functools
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyproj
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugin

import config as cfg
import openclsim_patches

openclsim_patches.apply()


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
        core.ContainerDependentMovable,
        core.HasResource,
        core.Processor,
        core.LoadingFunction,
        core.UnloadingFunction,
    ),
    {},
)

WeatheredMoveActivity = type(
    "WeatheredMoveActivity",
    (plugin.HasWeatherPluginActivity, model.MoveActivity),
    {},
)

WeatheredShiftActivity = type(
    "WeatheredShiftActivity",
    (plugin.HasWeatherPluginActivity, model.ShiftAmountActivity),
    {},
)

WeatheredBasicActivity = type(
    "WeatheredBasicActivity",
    (plugin.HasWeatherPluginActivity, model.BasicActivity),
    {},
)


@dataclass
class SimulationResult:
    """All objects of a finished simulation run."""
    env: simpy.Environment
    registry: dict
    duration_days: float
    start_date: object
    sites: dict
    vessels: dict
    activities: dict
    zero_shift_events: int = 0


def _sailing_time(p1, p2, speed_ms):
    """Sailing time (s) over the WGS84 geodesic between two points."""
    geod = pyproj.Geod(ellps="WGS84")
    _, _, dist = geod.inv(p1.x, p1.y, p2.x, p2.y)
    return dist / speed_ms


@functools.lru_cache(maxsize=4)
def _read_metocean(path_str, mtime):
    return pd.read_excel(path_str, index_col="Time")


def _load_metocean(path=None):
    """Read a metocean file (cached; re-read when the file changes)."""
    path = Path(path if path is not None else cfg.METOCEAN_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Metocean file not found: {path}\n"
            "Place it at code_simulation/data/metocean_era5.xlsx, set the "
            "environment variable FOWT_METOCEAN_PATH, or change "
            "METOCEAN_PATH in config.py."
        )
    return _read_metocean(str(path.resolve()), path.stat().st_mtime)


def _split_trips(n_units, n_vessels):
    """Trips per vessel: as equal as possible, larger shares first.

    25 units over 2 vessels gives [13, 12], over 3 gives [9, 8, 8], etc.
    """
    if not 1 <= n_vessels <= n_units:
        raise ValueError(
            f"N_VESSELS_PER_LEG must be between 1 and {n_units}, got {n_vessels}"
        )
    q, r = divmod(n_units, n_vessels)
    return [q + 1] * r + [q] * (n_vessels - r)


def run_simulation(verbose=True, start_date=None):
    """Run one simulation for config.SCENARIO from start_date (UTC datetime)."""
    if start_date is None:
        start_date = cfg.SIMULATION_START

    openclsim_patches.ZERO_SHIFT_EVENTS.clear()

    n_vessels = cfg.N_VESSELS_PER_LEG
    N_FLOATERS = cfg.N_TARGET
    VESSEL_REPS = _split_trips(N_FLOATERS, n_vessels)

    locs = cfg.get_locations()
    loc_manufacturing = locs["manufacturing"]
    loc_wet_storage = locs["wet_storage"]
    loc_integration = locs["integration"]
    loc_site = locs["site"]

    env = simpy.Environment(initial_time=start_date.timestamp())

    metocean_df_MP = _load_metocean(cfg.METOCEAN_PATH_MF or cfg.METOCEAN_PATH)
    metocean_df_WS = _load_metocean(cfg.METOCEAN_PATH_WS or cfg.METOCEAN_PATH)
    metocean_df_IP = _load_metocean(cfg.METOCEAN_PATH_IP or cfg.METOCEAN_PATH)
    metocean_df_Site = _load_metocean(cfg.METOCEAN_PATH_PS or cfg.METOCEAN_PATH)

    t_LtoWS = _sailing_time(loc_manufacturing, loc_wet_storage, cfg.VESSEL_SPEED_LOADED)
    t_WStoIP = _sailing_time(loc_wet_storage, loc_integration, cfg.VESSEL_SPEED_LOADED)
    t_IPtoSite = _sailing_time(loc_integration, loc_site, cfg.VESSEL_SPEED_LOADED)

    if verbose:
        print(f"Scenario {cfg.SCENARIO}, start {start_date:%Y-%m-%d}")
        print("Loaded sailing times:")
        print(f"  Leg 1  manufacturing -> wet storage : {t_LtoWS / 3600:6.2f} h")
        print(f"  Tow    wet storage   -> integration : {t_WStoIP / 3600:6.2f} h")
        print(f"  Leg 2  integration   -> site        : {t_IPtoSite / 3600:6.2f} h")
        print()
        print(f"Vessels: {n_vessels} per leg, {N_FLOATERS} floaters in total.")
        print("Round trips per vessel, per leg:")
        for k, reps in enumerate(VESSEL_REPS):
            print(f"  Vessel {k + 1}: {reps:2d} trips")
        print()

    crit_launching = plugin.WeatherCriterion(
        name="launching", condition="viol_launching",
        maximum=0, window_length=cfg.LAUNCH_TIME_WW)
    crit_sailing_LtoWS = plugin.WeatherCriterion(
        name="sailing_LtoWS", condition="viol_sailing_LtoWS",
        maximum=0, window_length=t_LtoWS)
    crit_sailing_WStoIP = plugin.WeatherCriterion(
        name="sailing_WStoIP", condition="viol_sailing_WStoIP",
        maximum=0, window_length=t_WStoIP)
    crit_integration = plugin.WeatherCriterion(
        name="integration", condition="viol_integration",
        maximum=0, window_length=cfg.INTEGRATION_WW)
    crit_nacelle = plugin.WeatherCriterion(
        name="nacelle", condition="viol_assembly_nac",
        maximum=0, window_length=cfg.ASSEMBLY_NACELLE_WW)
    crit_blade = plugin.WeatherCriterion(
        name="blade", condition="viol_assembly_blades",
        maximum=0, window_length=cfg.ASSEMBLY_BLADE_WW)
    crit_sailing_IPtoSite = plugin.WeatherCriterion(
        name="sailing_IPtoSite", condition="viol_sailing_IPtoSite",
        maximum=0, window_length=t_IPtoSite)
    crit_installation = plugin.WeatherCriterion(
        name="installation", condition="viol_installation",
        maximum=0, window_length=cfg.INSTALLATION_TIME_WW)
    crit_iac_hookup = plugin.WeatherCriterion(
        name="iac_hookup", condition="viol_IAChookup",
        maximum=0, window_length=cfg.IAC_HOOKUP_TIME_WW)
    crit_tte = plugin.WeatherCriterion(
        name="tte", condition="viol_TTE",
        maximum=0, window_length=cfg.TTE_TIME_WW)
    crit_wtg_commissioning = plugin.WeatherCriterion(
        name="wtg_commissioning", condition="viol_WTGcommissionning",
        maximum=0, window_length=cfg.WTG_COMMISSIONING_TIME_WW)

    raw_materials_buffer = Site(
        env=env, name="Raw materials buffer",
        geometry=loc_manufacturing,
        capacity=N_FLOATERS, level=N_FLOATERS)

    manufacturing_port = Site(
        env=env, name="Manufacturing floater port",
        geometry=loc_manufacturing,
        capacity=cfg.MANUFACTURING_CAPACITY, level=0)

    launch_berth = Site(
        env=env, name="Launch berth",
        geometry=loc_manufacturing, capacity=1, level=0)

    post_launch = Site(
        env=env, name="Post-launch staging (launch berth departure)",
        geometry=loc_manufacturing, capacity=1, level=0)

    wet_storage_1 = Site(
        env=env, name="Wet storage 1",
        geometry=loc_manufacturing,
        capacity=cfg.BERTH_STORAGE_MF_CAPACITY, level=0)

    wet_storage = Site(
        env=env, name="Wet storage",
        geometry=loc_wet_storage, capacity=cfg.WET_STORAGE_CAPACITY, level=0)

    _ws2_cap = cfg.WET_STORAGE_CAPACITY if cfg.WET_STORAGE_CAPACITY >= 1 else 1
    _ws2_big = N_FLOATERS + _ws2_cap
    ws2_free = Site(
        env=env, name="WS2 free-slot tokens",
        geometry=loc_wet_storage, capacity=_ws2_cap, level=_ws2_cap)
    ws2_sink = Site(
        env=env, name="WS2 claimed-token sink",
        geometry=loc_wet_storage, capacity=_ws2_big, level=0)
    ws2_source = Site(
        env=env, name="WS2 token source",
        geometry=loc_wet_storage, capacity=_ws2_big, level=_ws2_big)

    tower_buffer = Site(
        env=env, name="Tower buffer (parallel line)",
        geometry=loc_integration, capacity=N_FLOATERS, level=0)

    tower_raw = Site(
        env=env, name="Tower raw materials",
        geometry=loc_integration,
        capacity=N_FLOATERS, level=N_FLOATERS)

    tower_consumed = Site(
        env=env, name="Towers consumed in turbines",
        geometry=loc_integration, capacity=N_FLOATERS, level=0)

    berth_ip1 = Site(
        env=env, name="Berth storage IP1",
        geometry=loc_integration,
        capacity=cfg.BERTH_STORAGE_IP1_CAPACITY, level=0)
    pre_integration = Site(
        env=env, name="Pre-integration staging",
        geometry=loc_integration, capacity=1, level=0)

    _ip1_cap = cfg.BERTH_STORAGE_IP1_CAPACITY if cfg.BERTH_STORAGE_IP1_CAPACITY >= 1 else 1
    _big = N_FLOATERS + _ip1_cap
    ip1_free = Site(
        env=env, name="IP1 free-berth tokens",
        geometry=loc_wet_storage, capacity=_ip1_cap, level=_ip1_cap)
    ip1_sink = Site(
        env=env, name="IP1 claimed-token sink",
        geometry=loc_wet_storage, capacity=_big, level=0)
    ip1_source = Site(
        env=env, name="IP1 token source",
        geometry=loc_wet_storage, capacity=_big, level=_big)

    integration_floater_in = Site(
        env=env, name="Integration port (floater in-buffer)",
        geometry=loc_integration,
        capacity=1, level=0)

    integration_buffer_mid = Site(
        env=env, name="Integration port (mid-buffer A->B)",
        geometry=loc_integration, capacity=1, level=0)

    ip2_cap = cfg.BERTH_STORAGE_IP2_CAPACITY
    wet_storage_3 = Site(
        env=env, name="Wet storage 3",
        geometry=loc_integration,
        capacity=ip2_cap, level=0)

    post_commissioning = Site(
        env=env, name="Post-commissioning staging",
        geometry=loc_integration, capacity=1, level=0)

    site = Site(
        env=env, name="Offshore site",
        geometry=loc_site, capacity=N_FLOATERS, level=0)

    install_signal_source = Site(
        env=env, name="Install signal source",
        geometry=loc_site, capacity=N_FLOATERS, level=N_FLOATERS)

    installed_queue = Site(
        env=env, name="Installed queue (awaiting stringing)",
        geometry=loc_site, capacity=N_FLOATERS, level=0)

    commissioned = Site(
        env=env, name="Commissioned turbines",
        geometry=loc_site, capacity=N_FLOATERS, level=0)

    production_processor = TransportProcessingResource(
        env=env, name="Production team",
        geometry=loc_manufacturing,
        loading_rate=1, unloading_rate=1,
        capacity=1, level=0,
        compute_v=lambda x: 1)

    launch_shuttle = TransportProcessingResource(
        env=env, name="Launch berth shuttle (WS1 -> post-launch)",
        geometry=loc_manufacturing,
        loading_rate=1, unloading_rate=1,
        capacity=1, level=0,
        compute_v=lambda x: 1)

    floater_carriers = [
        TransportProcessingResource(
            env=env, name=f"Floater carrier {k + 1}",
            geometry=loc_manufacturing,
            loading_rate=1, unloading_rate=1,
            capacity=1, level=0,
            compute_v=lambda x: cfg.VESSEL_SPEED_LOADED if x > 0
            else cfg.VESSEL_SPEED_EMPTY)
        for k in range(n_vessels)
    ]

    tugs = [
        TransportProcessingResource(
            env=env, name=f"Tug {k + 1} (wet storage -> integration)",
            geometry=loc_wet_storage,
            loading_rate=1, unloading_rate=1,
            capacity=1, level=0,
            compute_v=lambda x: cfg.VESSEL_SPEED_LOADED if x > 0
            else cfg.VESSEL_SPEED_EMPTY)
        for k in range(n_vessels)
    ]
    tower_team = TransportProcessingResource(
        env=env, name="Tower production line",
        geometry=loc_integration,
        loading_rate=1, unloading_rate=1, capacity=1, level=0,
        compute_v=lambda x: 1)

    integration_team = TransportProcessingResource(
        env=env, name="Integration team (integration + WTG assembly)",
        geometry=loc_integration,
        loading_rate=1, unloading_rate=1, capacity=1, level=0,
        compute_v=lambda x: 1)

    commissioning_team = TransportProcessingResource(
        env=env, name="Commissioning & testing team",
        geometry=loc_integration,
        loading_rate=1, unloading_rate=1, capacity=1, level=0,
        compute_v=lambda x: 1)

    integration_shuttle = TransportProcessingResource(
        env=env, name="Integration shuttle (buffer -> staging refills)",
        geometry=loc_integration,
        loading_rate=1, unloading_rate=1, capacity=1, level=0,
        compute_v=lambda x: 1)

    ip1_token_mover = TransportProcessingResource(
        env=env, name="IP1 berth-token mover (WS2)",
        geometry=loc_wet_storage,
        loading_rate=1, unloading_rate=1, capacity=1, level=0,
        compute_v=lambda x: 1)

    turbine_carriers = [
        TransportProcessingResource(
            env=env, name=f"Turbine carrier {k + 1}",
            geometry=loc_integration,
            loading_rate=1, unloading_rate=1,
            capacity=1, level=0,
            compute_v=lambda x: cfg.VESSEL_SPEED_LOADED if x > 0
            else cfg.VESSEL_SPEED_EMPTY)
        for k in range(n_vessels)
    ]

    CLV = TransportProcessingResource(
        env=env, name="CLV (TT&E and WTG commissioning)",
        geometry=loc_site,
        loading_rate=1, unloading_rate=1,
        capacity=1, level=0,
        compute_v=lambda x: cfg.VESSEL_SPEED_CLV)

    registry = {}

    production_subprocesses = [
        model.BasicActivity(
            env=env, name="manufacturing floater",
            registry=registry, duration=cfg.PRODUCTION_TIME,
            additional_logs=[manufacturing_port, raw_materials_buffer]),
        model.ShiftAmountActivity(
            env=env, name="floater off the production line",
            registry=registry, processor=production_processor,
            origin=raw_materials_buffer, destination=production_processor,
            amount=1, duration=0),
        model.BasicActivity(
            env=env, name="wait for stockyard space",
            registry=registry, duration=0,
            additional_logs=[production_processor],
            start_event=[{
                "type": "container", "concept": manufacturing_port,
                "state": "lt",
                "level": manufacturing_port.container.get_capacity()}]),
        model.ShiftAmountActivity(
            env=env, name="floater into stockyard",
            registry=registry, processor=production_processor,
            origin=production_processor, destination=manufacturing_port,
            amount=1, duration=0),
    ]
    production_sequence = model.SequentialActivity(
        env=env, name="produce one floater",
        registry=registry, sub_processes=production_subprocesses)
    production_activity = model.RepeatActivity(
        env=env, name="A. Production of all floaters",
        registry=registry, sub_processes=[production_sequence],
        repetitions=N_FLOATERS)

    ws1_active = cfg.BERTH_STORAGE_MF_CAPACITY >= 1
    ws1_target = wet_storage_1 if ws1_active else post_launch
    ip1_active = cfg.BERTH_STORAGE_IP1_CAPACITY >= 1
    ip1_target = berth_ip1 if ip1_active else pre_integration
    ws3_active = ip2_cap >= 1
    ws3_target = wet_storage_3 if ws3_active else post_commissioning

    launch_subprocesses = [
        model.BasicActivity(
            env=env, name="waiting for 1 floaters at manufacturing port",
            registry=registry, duration=0,
            additional_logs=[production_processor],
            start_event=[{"type": "container", "concept": manufacturing_port,
                          "state": "ge", "level": 1}]),
        model.BasicActivity(
            env=env, name="wait for launch berth space",
            registry=registry, duration=0,
            additional_logs=[production_processor],
            start_event=[{"type": "container", "concept": launch_berth,
                          "state": "lt", "level": 1}]),
        WeatheredBasicActivity(
            env=env, name="[WW] launching 1 floater",
            registry=registry, duration=0,
            additional_logs=[production_processor],
            metocean_criteria=crit_launching, metocean_df=metocean_df_MP),
        model.ShiftAmountActivity(
            env=env, name="floater 1 into water",
            registry=registry, processor=production_processor,
            origin=manufacturing_port, destination=launch_berth,
            amount=1, duration=cfg.LAUNCH_TIME),
        model.BasicActivity(
            env=env, name="wait for wet storage 1 space",
            registry=registry, duration=0,
            additional_logs=[production_processor],
            start_event=[{"type": "container", "concept": ws1_target,
                          "state": "lt",
                          "level": ws1_target.container.get_capacity()}]),
        model.ShiftAmountActivity(
            env=env, name="floater into wet storage 1",
            registry=registry, processor=production_processor,
            origin=launch_berth, destination=ws1_target,
            amount=1, duration=0),
    ]
    launch_sequence = model.SequentialActivity(
        env=env, name="launch single floater",
        registry=registry, sub_processes=launch_subprocesses)
    launch_activity = model.RepeatActivity(
        env=env, name="A2. Launching floaters",
        registry=registry, sub_processes=[launch_sequence],
        repetitions=N_FLOATERS)

    pl_refill_subprocesses = [
        model.BasicActivity(
            env=env, name="wait for empty post-launch + floater in WS1",
            registry=registry, duration=0,
            additional_logs=[launch_shuttle],
            start_event=[
                {"type": "container", "concept": post_launch,
                 "state": "lt", "level": 1},
                {"type": "container", "concept": wet_storage_1,
                 "state": "ge", "level": 1},
            ]),
        model.ShiftAmountActivity(
            env=env, name="stage floater WS1 -> post-launch",
            registry=registry, processor=launch_shuttle,
            origin=wet_storage_1, destination=post_launch,
            amount=1, duration=0,
            start_event=[{"type": "container", "concept": wet_storage_1,
                          "state": "ge", "level": 1}]),
    ]
    pl_refill_sequence = model.SequentialActivity(
        env=env, name="refill post-launch staging",
        registry=registry, sub_processes=pl_refill_subprocesses)
    pl_refill_activity = model.RepeatActivity(
        env=env, name="A3. Refill post-launch from WS1",
        registry=registry, sub_processes=[pl_refill_sequence],
        repetitions=N_FLOATERS)

    def build_floater_leg(carrier, k):
        subprocesses = [
            model.MoveActivity(
                env=env, name=f"sailing empty to launch berth [FC{k + 1}]",
                registry=registry, mover=carrier,
                destination=post_launch),
            model.BasicActivity(
                env=env, name=f"wait for staged floater + WS2 space [FC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                start_event=[
                    {"type": "container", "concept": post_launch,
                     "state": "ge", "level": 1},
                ]),
            WeatheredBasicActivity(
                env=env, name=f"[WW] wait for sailing window (leg 1) [FC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                metocean_criteria=crit_sailing_LtoWS,
                metocean_df=metocean_df_MP),
            model.ShiftAmountActivity(
                env=env, name=f"loading 1 floater from launch berth [FC{k + 1}]",
                registry=registry, processor=carrier,
                origin=post_launch, destination=carrier,
                amount=1, duration=0,
                start_event=[{"type": "container", "concept": post_launch,
                              "state": "ge", "level": 1}]),
            model.MoveActivity(
                env=env, name=f"sailing loaded to wet storage [FC{k + 1}]",
                registry=registry, mover=carrier,
                destination=wet_storage),
            model.ShiftAmountActivity(
                env=env, name=f"claim WS2 slot [FC{k + 1}]",
                registry=registry, processor=carrier,
                origin=ws2_free, destination=ws2_sink,
                amount=1, duration=0),
            model.ShiftAmountActivity(
                env=env, name=f"delivering floater at wet storage [FC{k + 1}]",
                registry=registry, processor=carrier,
                origin=carrier, destination=wet_storage,
                amount=1, duration=0),
        ]
        sequence = model.SequentialActivity(
            env=env, name=f"floater leg cycle (FC{k + 1})",
            registry=registry, sub_processes=subprocesses)
        return model.RepeatActivity(
            env=env,
            name=f"B. Floater carrier {k + 1} (Manufacturing -> WS)",
            registry=registry, sub_processes=[sequence],
            repetitions=VESSEL_REPS[k])

    floater_leg_vessels = [
        build_floater_leg(c, k) for k, c in enumerate(floater_carriers)
    ]
    floater_leg_activity = model.ParallelActivity(
        env=env, name="B. Floater leg (all carriers, parallel)",
        registry=registry, sub_processes=floater_leg_vessels)

    def build_tug_leg(tug, k):
        subprocesses = [
            model.MoveActivity(
                env=env, name=f"tug sailing to wet storage [TUG{k + 1}]",
                registry=registry, mover=tug, destination=wet_storage),

            model.BasicActivity(
                env=env, name=f"waiting for floater at wet storage [TUG{k + 1}]",
                registry=registry, duration=0, additional_logs=[tug],
                start_event=[
                    {"type": "container", "concept": wet_storage,
                     "state": "ge", "level": 1},
                ]),
            model.ShiftAmountActivity(
                env=env, name=f"claim IP1 berth slot [TUG{k + 1}]",
                registry=registry, processor=tug,
                origin=ip1_free, destination=ip1_sink,
                amount=1, duration=0),
            WeatheredBasicActivity(
                env=env, name=f"[WW] wait for sailing window [TUG{k + 1}]",
                registry=registry, duration=0, additional_logs=[tug],
                metocean_criteria=crit_sailing_WStoIP,
                metocean_df=metocean_df_WS),
            model.ShiftAmountActivity(
                env=env, name=f"tug picks up floater from wet storage [TUG{k + 1}]",
                registry=registry, processor=tug,
                origin=wet_storage, destination=tug,
                amount=1, duration=0),
            model.ShiftAmountActivity(
                env=env, name=f"release WS2 slot [TUG{k + 1}]",
                registry=registry, processor=tug,
                origin=ws2_source, destination=ws2_free,
                amount=1, duration=0),
            model.MoveActivity(
                env=env, name=f"tug towing loaded to integration port [TUG{k + 1}]",
                registry=registry, mover=tug,
                destination=ip1_target),
            model.ShiftAmountActivity(
                env=env, name=f"tug delivers floater at berth IP1 [TUG{k + 1}]",
                registry=registry, processor=tug,
                origin=tug, destination=ip1_target,
                amount=1, duration=0),
        ]
        sequence = model.SequentialActivity(
            env=env, name=f"tug cycle (TUG{k + 1})",
            registry=registry, sub_processes=subprocesses)
        return model.RepeatActivity(
            env=env, name=f"B2. Tug {k + 1} (WS -> Integration Port)",
            registry=registry, sub_processes=[sequence],
            repetitions=VESSEL_REPS[k])

    tug_leg_vessels = [
        build_tug_leg(t, k) for k, t in enumerate(tugs)
    ]
    tug_leg_activity = model.ParallelActivity(
        env=env, name="B2. Tug leg (all tugs, parallel)",
        registry=registry, sub_processes=tug_leg_vessels)

    tower_line_subprocesses = [
        model.ShiftAmountActivity(
            env=env, name="tower onto production line",
            registry=registry, processor=tower_team,
            origin=tower_raw, destination=tower_team,
            amount=1, duration=0,
            start_event=[{"type": "container", "concept": tower_raw,
                          "state": "ge", "level": 1}]),
        model.ShiftAmountActivity(
            env=env, name="tower into tower buffer",
            registry=registry, processor=tower_team,
            origin=tower_team, destination=tower_buffer,
            amount=1, duration=0),
    ]
    tower_line_sequence = model.SequentialActivity(
        env=env, name="produce one tower",
        registry=registry, sub_processes=tower_line_subprocesses)
    tower_line_activity = model.RepeatActivity(
        env=env, name="C0. Tower production line (parallel)",
        registry=registry, sub_processes=[tower_line_sequence],
        repetitions=N_FLOATERS)

    integration_subprocesses = [
        model.ShiftAmountActivity(
            env=env, name="move floater from pre-integration to integration quay",
            registry=registry, processor=integration_team,
            origin=pre_integration, destination=integration_floater_in,
            amount=1, duration=0,
            start_event=[
                {"type": "container", "concept": pre_integration,
                 "state": "ge", "level": 1},
                {"type": "container", "concept": tower_buffer,
                 "state": "ge", "level": 1},
                {"type": "container", "concept": integration_buffer_mid,
                 "state": "lt",
                 "level": integration_buffer_mid.container.get_capacity()},
            ]),
        model.ShiftAmountActivity(
            env=env, name="intake floater",
            registry=registry, processor=integration_team,
            origin=integration_floater_in, destination=integration_team,
            amount=1, duration=0),
        model.ShiftAmountActivity(
            env=env, name="claim tower from buffer",
            registry=registry, processor=integration_team,
            origin=tower_buffer, destination=tower_consumed,
            amount=1, duration=0),
        WeatheredBasicActivity(
            env=env, name="[WW] integration toppart",
            registry=registry, duration=cfg.INTEGRATION_TIME,
            additional_logs=[integration_team],
            metocean_criteria=crit_integration, metocean_df=metocean_df_IP),
        WeatheredBasicActivity(
            env=env, name="[WW] assembly nacelle",
            registry=registry, duration=cfg.ASSEMBLY_NC_TOT,
            additional_logs=[integration_team],
            metocean_criteria=crit_nacelle, metocean_df=metocean_df_IP),
        WeatheredBasicActivity(
            env=env, name="[WW] assembly blade 1",
            registry=registry, duration=cfg.ASSEMBLY_NC_TOT,
            additional_logs=[integration_team],
            metocean_criteria=crit_blade, metocean_df=metocean_df_IP),
        WeatheredBasicActivity(
            env=env, name="[WW] assembly blade 2",
            registry=registry, duration=cfg.ASSEMBLY_NC_TOT,
            additional_logs=[integration_team],
            metocean_criteria=crit_blade, metocean_df=metocean_df_IP),
        WeatheredBasicActivity(
            env=env, name="[WW] assembly blade 3",
            registry=registry, duration=cfg.ASSEMBLY_NC_TOT,
            additional_logs=[integration_team],
            metocean_criteria=crit_blade, metocean_df=metocean_df_IP),
        model.ShiftAmountActivity(
            env=env, name="handover to mid-buffer",
            registry=registry, processor=integration_team,
            origin=integration_team, destination=integration_buffer_mid,
            amount=1, duration=0),
    ]
    if not ip1_active:
        integration_subprocesses.insert(1, model.ShiftAmountActivity(
            env=env, name="release IP1 berth slot (bypass)",
            registry=registry, processor=ip1_token_mover,
            origin=ip1_source, destination=ip1_free,
            amount=1, duration=0))

    integration_sequence = model.SequentialActivity(
        env=env, name="integration cycle",
        registry=registry, sub_processes=integration_subprocesses)
    assembly_activity_A = model.RepeatActivity(
        env=env, name="C1. Integration team (integration + WTG assembly)",
        registry=registry, sub_processes=[integration_sequence],
        repetitions=N_FLOATERS)

    assembly_B_subprocesses = [
        model.ShiftAmountActivity(
            env=env, name="intake from mid-buffer",
            registry=registry, processor=commissioning_team,
            origin=integration_buffer_mid, destination=commissioning_team,
            amount=1, duration=0,
            start_event=[{"type": "container", "concept": integration_buffer_mid,
                          "state": "ge", "level": 1}]),
        model.BasicActivity(
            env=env, name="commissioning & testing",
            registry=registry, duration=cfg.COMMISSIONING_TESTING_TIME,
            additional_logs=[commissioning_team]),
        model.BasicActivity(
            env=env, name="wait for wet storage 3 space",
            registry=registry, duration=0,
            additional_logs=[commissioning_team],
            start_event=[{"type": "container", "concept": ws3_target,
                          "state": "lt",
                          "level": ws3_target.container.get_capacity()}]),
        model.ShiftAmountActivity(
            env=env, name="release commissioned turbine to wet storage 3",
            registry=registry, processor=commissioning_team,
            origin=commissioning_team, destination=ws3_target,
            amount=1, duration=0),
    ]
    assembly_B_sequence = model.SequentialActivity(
        env=env, name="commissioning & testing cycle",
        registry=registry, sub_processes=assembly_B_subprocesses)
    assembly_activity_B = model.RepeatActivity(
        env=env, name="C2. Commissioning & testing team",
        registry=registry, sub_processes=[assembly_B_sequence],
        repetitions=N_FLOATERS)

    pre_int_refill_subprocesses = [
        model.BasicActivity(
            env=env, name="wait for empty pre-integration + floater in IP1",
            registry=registry, duration=0,
            additional_logs=[integration_shuttle],
            start_event=[
                {"type": "container", "concept": pre_integration,
                 "state": "lt", "level": 1},
                {"type": "container", "concept": berth_ip1,
                 "state": "ge", "level": 1},
            ]),
        model.ShiftAmountActivity(
            env=env, name="stage floater IP1 -> pre-integration",
            registry=registry, processor=integration_shuttle,
            origin=berth_ip1, destination=pre_integration,
            amount=1, duration=0,
            start_event=[{"type": "container", "concept": berth_ip1,
                          "state": "ge", "level": 1}]),
        model.ShiftAmountActivity(
            env=env, name="release IP1 berth slot",
            registry=registry, processor=ip1_token_mover,
            origin=ip1_source, destination=ip1_free,
            amount=1, duration=0),
    ]
    pre_int_refill_sequence = model.SequentialActivity(
        env=env, name="refill pre-integration staging",
        registry=registry, sub_processes=pre_int_refill_subprocesses)
    pre_int_refill_activity = model.RepeatActivity(
        env=env, name="C0b. Refill pre-integration from IP1",
        registry=registry, sub_processes=[pre_int_refill_sequence],
        repetitions=N_FLOATERS)

    post_comm_refill_subprocesses = [
        model.BasicActivity(
            env=env, name="wait for empty post-commissioning + turbine in IP2",
            registry=registry, duration=0,
            additional_logs=[integration_shuttle],
            start_event=[
                {"type": "container", "concept": post_commissioning,
                 "state": "lt", "level": 1},
                {"type": "container", "concept": wet_storage_3,
                 "state": "ge", "level": 1},
            ]),
        model.ShiftAmountActivity(
            env=env, name="stage turbine IP2 -> post-commissioning",
            registry=registry, processor=integration_shuttle,
            origin=wet_storage_3, destination=post_commissioning,
            amount=1, duration=0,
            start_event=[{"type": "container", "concept": wet_storage_3,
                          "state": "ge", "level": 1}]),
    ]
    post_comm_refill_sequence = model.SequentialActivity(
        env=env, name="refill post-commissioning staging",
        registry=registry, sub_processes=post_comm_refill_subprocesses)
    post_comm_refill_activity = model.RepeatActivity(
        env=env, name="C3. Refill post-commissioning from IP2",
        registry=registry, sub_processes=[post_comm_refill_sequence],
        repetitions=N_FLOATERS)

    def build_turbine_leg(carrier, k):
        subprocesses = [
            model.MoveActivity(
                env=env, name=f"[SE]sailing empty to integration port [TC{k + 1}]",
                registry=registry, mover=carrier,
                destination=post_commissioning),

            model.BasicActivity(
                env=env, name=f"waiting for turbine availability [TC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                start_event=[{"type": "container",
                              "concept": post_commissioning,
                              "state": "ge", "level": 1}]),
            WeatheredBasicActivity(
                env=env, name=f"[WW] wait for sailing window (leg 2) [TC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                metocean_criteria=crit_sailing_IPtoSite,
                metocean_df=metocean_df_Site),
            model.ShiftAmountActivity(
                env=env, name=f"[SE]loading integrated turbine [TC{k + 1}]",
                registry=registry, processor=carrier,
                origin=post_commissioning, destination=carrier,
                amount=1, duration=0,
                start_event=[{"type": "container",
                              "concept": post_commissioning,
                              "state": "ge", "level": 1}]),
            model.MoveActivity(
                env=env, name=f"sailing loaded to site [TC{k + 1}]",
                registry=registry, mover=carrier, destination=site),
            model.ShiftAmountActivity(
                env=env, name=f"[SE]offloading turbine at site [TC{k + 1}]",
                registry=registry, processor=carrier,
                origin=carrier, destination=site,
                amount=1, duration=0),
            WeatheredBasicActivity(
                env=env, name=f"[WW] wait for installation window [TC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                metocean_criteria=crit_installation,
                metocean_df=metocean_df_Site),
            WeatheredBasicActivity(
                env=env, name=f"[SE]installation at site [TC{k + 1}]",
                registry=registry, duration=cfg.INSTALLATION_TIME,
                additional_logs=[carrier],
                metocean_criteria=crit_installation,
                metocean_df=metocean_df_Site),
            WeatheredBasicActivity(
                env=env, name=f"[WW] wait for IAC hookup window [TC{k + 1}]",
                registry=registry, duration=0,
                additional_logs=[carrier],
                metocean_criteria=crit_iac_hookup,
                metocean_df=metocean_df_Site),
            WeatheredBasicActivity(
                env=env, name=f"[SE]IAC hookup at site [TC{k + 1}]",
                registry=registry, duration=cfg.IAC_HOOKUP_TIME,
                additional_logs=[carrier],
                metocean_criteria=crit_iac_hookup,
                metocean_df=metocean_df_Site),
            model.ShiftAmountActivity(
                env=env, name=f"signal: installation done -> installed_queue [TC{k + 1}]",
                registry=registry, processor=carrier,
                origin=install_signal_source, destination=installed_queue,
                amount=1, duration=0),
        ]
        sequence = model.SequentialActivity(
            env=env, name=f"turbine leg cycle (TC{k + 1})",
            registry=registry, sub_processes=subprocesses)
        return model.RepeatActivity(
            env=env, name=f"D. Turbine carrier {k + 1} (Integration -> Site)",
            registry=registry, sub_processes=[sequence],
            repetitions=VESSEL_REPS[k])

    turbine_leg_vessels = [
        build_turbine_leg(c, k) for k, c in enumerate(turbine_carriers)
    ]
    turbine_leg_activity = model.ParallelActivity(
        env=env, name="D. Turbine leg (all carriers, parallel)",
        registry=registry, sub_processes=turbine_leg_vessels)

    SHIFTS_PER_TURBINE = getattr(cfg, "SHIFTS_PER_TURBINE_OVERRIDE",
                                 cfg.SHIFTS_PER_TURBINE)

    tte_shift_sequence = model.SequentialActivity(
        env=env, name="TTE shift",
        registry=registry, sub_processes=[
            WeatheredBasicActivity(
                env=env, name="[WW] wait for TTE window",
                registry=registry, duration=0, additional_logs=[CLV],
                metocean_criteria=crit_tte, metocean_df=metocean_df_Site),
            WeatheredBasicActivity(
                env=env, name="[SE]TTE at site",
                registry=registry, duration=cfg.TTE_TIME,
                additional_logs=[CLV],
                metocean_criteria=crit_tte, metocean_df=metocean_df_Site),
        ])
    tte_shift_activity = model.RepeatActivity(
        env=env, name="TTE (all shifts)",
        registry=registry, sub_processes=[tte_shift_sequence],
        repetitions=SHIFTS_PER_TURBINE)

    wtg_shift_sequence = model.SequentialActivity(
        env=env, name="WTG commissioning shift",
        registry=registry, sub_processes=[
            WeatheredBasicActivity(
                env=env, name="[WW] wait for WTG commissioning window",
                registry=registry, duration=0, additional_logs=[CLV],
                metocean_criteria=crit_wtg_commissioning,
                metocean_df=metocean_df_Site),
            WeatheredBasicActivity(
                env=env, name="[SE]WTG commissioning at site",
                registry=registry, duration=cfg.WTG_COMMISSIONING_TIME,
                additional_logs=[CLV],
                metocean_criteria=crit_wtg_commissioning,
                metocean_df=metocean_df_Site),
        ])
    wtg_shift_activity = model.RepeatActivity(
        env=env, name="WTG commissioning (all shifts)",
        registry=registry, sub_processes=[wtg_shift_sequence],
        repetitions=SHIFTS_PER_TURBINE)
    stringing_subprocesses = [
        model.BasicActivity(
            env=env, name="wait for installed turbine",
            registry=registry, duration=0, additional_logs=[CLV],
            start_event=[{"type": "container", "concept": installed_queue,
                          "state": "ge", "level": 1}]),
        model.ShiftAmountActivity(
            env=env, name="claim installed turbine",
            registry=registry, processor=CLV,
            origin=installed_queue, destination=CLV,
            amount=1, duration=0),
        tte_shift_activity,
        wtg_shift_activity,
        model.ShiftAmountActivity(
            env=env, name="release commissioned turbine",
            registry=registry, processor=CLV,
            origin=CLV, destination=commissioned,
            amount=1, duration=0),
    ]
    stringing_sequence = model.SequentialActivity(
        env=env, name="commissioning cycle",
        registry=registry, sub_processes=stringing_subprocesses)
    stringing_activity = model.RepeatActivity(
        env=env, name="E. TTE + WTG commissioning (per turbine)",
        registry=registry, sub_processes=[stringing_sequence],
        repetitions=N_FLOATERS)

    procs = [
        production_activity,
        launch_activity,
    ]
    if ws1_active:
        procs.append(pl_refill_activity)
    procs += [
        floater_leg_activity,
        tug_leg_activity,
    ]
    if ip1_active:
        procs.append(pre_int_refill_activity)
    procs += [
        tower_line_activity,
        assembly_activity_A,
        assembly_activity_B,
    ]
    if ws3_active:
        procs.append(post_comm_refill_activity)
    procs += [
        turbine_leg_activity,
        stringing_activity,
    ]
    model.register_processes(procs)

    timed_out = []

    def wait_for_completion():
        last_print = env.now
        last_level = -1
        while commissioned.container.get_level() < N_FLOATERS:
            yield env.timeout(cfg.HOUR)
            level = commissioned.container.get_level()
            if verbose and (level != last_level
                            or (env.now - last_print) > 30 * cfg.DAY):
                t = dt.datetime.fromtimestamp(env.now, tz=dt.timezone.utc)
                print(f"  [{t:%Y-%m-%d}] commissioned: {level}/{N_FLOATERS}")
                print(f"    manufacturing_port:     {manufacturing_port.container.get_level()}")
                print(f"    launch_berth:           {launch_berth.container.get_level()}")
                print(f"    wet_storage_1:          {wet_storage_1.container.get_level()}")
                print(f"    post_launch:            {post_launch.container.get_level()}")
                print(f"    wet_storage (WS2):      {wet_storage.container.get_level()}")
                print(f"    berth_ip1:              {berth_ip1.container.get_level()}")
                print(f"    pre_integration:        {pre_integration.container.get_level()}")
                print(f"    integration_floater_in: {integration_floater_in.container.get_level()}")
                print(f"    integration_buffer_mid: {integration_buffer_mid.container.get_level()}")
                print(f"    wet_storage_3 (IP2):    {wet_storage_3.container.get_level()}")
                print(f"    post_commissioning:     {post_commissioning.container.get_level()}")
                print(f"    installed_queue:        {installed_queue.container.get_level()}")
                print(f"    tower_buffer:           {tower_buffer.container.get_level()}")
                print(f"    site:                   {site.container.get_level()}")
                print(f"    integration_team_carry: {integration_team.container.get_level()}")
                print(f"    commissioning_team:     {commissioning_team.container.get_level()}")
                print(f"    CLV:                    {CLV.container.get_level()}")
                last_print = env.now
                last_level = level
            if (env.now - start_date.timestamp()) > 10 * 365 * cfg.DAY:
                timed_out.append(level)
                if not done_event.triggered:
                    done_event.succeed()
                break

    done_event = env.event()

    def signal_done():
        while commissioned.container.get_level() < N_FLOATERS:
            yield env.timeout(cfg.HOUR)
        if not done_event.triggered:
            done_event.succeed()

    env.process(wait_for_completion())
    env.process(signal_done())
    env.run(until=done_event)

    if timed_out:
        raise RuntimeError(
            f"Scenario {cfg.SCENARIO}, start {start_date:%Y-%m-%d}: only "
            f"{timed_out[0]}/{N_FLOATERS} turbines commissioned after 10 years "
            "of simulated time (probable deadlock)."
        )

    duration_days = (env.now - start_date.timestamp()) / cfg.DAY

    n_zero = len(openclsim_patches.ZERO_SHIFT_EVENTS)
    if n_zero:
        warnings.warn(
            f"{n_zero} shift(s) into a full destination were skipped "
            f"(first: {openclsim_patches.ZERO_SHIFT_EVENTS[0]}); "
            "results of this run need checking.")

    if verbose:
        end_dt = dt.datetime.fromtimestamp(env.now, tz=dt.timezone.utc)
        print(f"Start date: {start_date:%Y-%m-%d}")
        print(f"Simulation ended on {end_dt:%Y-%m-%d %H:%M} UTC")
        print(f"Total duration: {duration_days:.2f} days "
              f"({duration_days / 365:.2f} years)")
        print(f"Duration per turbine: {duration_days / N_FLOATERS:.2f} days")
        print()

    return SimulationResult(
        env=env,
        registry=registry,
        duration_days=duration_days,
        start_date=start_date,
        sites={
            "raw_materials_buffer": raw_materials_buffer,
            "manufacturing_port": manufacturing_port,
            "launch_berth": launch_berth,
            "wet_storage_1": wet_storage_1,
            "post_launch": post_launch,
            "wet_storage": wet_storage,
            "tower_buffer": tower_buffer,
            "tower_raw": tower_raw,
            "tower_consumed": tower_consumed,
            "berth_ip1": berth_ip1,
            "pre_integration": pre_integration,
            "integration_floater_in": integration_floater_in,
            "integration_buffer_mid": integration_buffer_mid,
            "wet_storage_3": wet_storage_3,
            "post_commissioning": post_commissioning,
            "site": site,
            "install_signal_source": install_signal_source,
            "installed_queue": installed_queue,
            "commissioned": commissioned,
        },
        vessels={
            "production_processor": production_processor,
            "launch_shuttle": launch_shuttle,
            "floater_carriers": floater_carriers,
            "tugs": tugs,
            "tower_team": tower_team,
            "integration_team": integration_team,
            "integration_shuttle": integration_shuttle,
            "ip1_token_mover": ip1_token_mover,
            "commissioning_team": commissioning_team,
            "turbine_carriers": turbine_carriers,
            "CLV": CLV,
        },
        activities={
            "production_activity": production_activity,
            "launch_activity": launch_activity,
            "pl_refill_activity": pl_refill_activity,
            "floater_leg_activity": floater_leg_activity,
            "tug_leg_activity": tug_leg_activity,
            "pre_int_refill_activity": pre_int_refill_activity,
            "post_comm_refill_activity": post_comm_refill_activity,
            "floater_leg_activities": floater_leg_vessels,
            "tug_leg_activities": tug_leg_vessels,
            "tower_line_activity": tower_line_activity,
            "assembly_activity_A": assembly_activity_A,
            "assembly_activity_B": assembly_activity_B,
            "turbine_leg_activity": turbine_leg_activity,
            "turbine_leg_activities": turbine_leg_vessels,
            "stringing_activity": stringing_activity,
        },
        zero_shift_events=n_zero,
    )
