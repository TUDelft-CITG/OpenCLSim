"""Model parameters for the FOWT installation-chain simulation.

Units: durations in seconds (use HOUR / DAY), speeds in m/s, positions as
WGS84 lon/lat. Distances between nodes are not parameters: they follow from
the node coordinates of the selected SCENARIO in LOCATION_SCENARIOS.
"""

import datetime as dt
import os
from pathlib import Path

import shapely.geometry

HOUR = 3600
DAY = 24 * HOUR
YEAR = 365 * DAY

SIMULATION_START = dt.datetime(2017, 1, 1, 0, 0, tzinfo=dt.timezone.utc)

START_DATES = [
    dt.datetime(2017 + (2 * i) // 12, 1 + (2 * i) % 12, 1,
                tzinfo=dt.timezone.utc)
    for i in range(10)
]

DATA_DIR = Path(__file__).resolve().parent / "data"
METOCEAN_PATH = Path(os.environ.get("FOWT_METOCEAN_PATH",
                                    DATA_DIR / "metocean_era5.xlsx"))

METOCEAN_PATH_MF = None
METOCEAN_PATH_WS = None
METOCEAN_PATH_IP = None
METOCEAN_PATH_PS = None

SCENARIO = "100,10,100"

N_TARGET = 25
NUM_FLOATERS = N_TARGET
N_VESSELS_PER_LEG = 2

MANUFACTURING_CAPACITY = 6

BERTH_STORAGE_MF_CAPACITY = 1
WET_STORAGE_CAPACITY = 100
BERTH_STORAGE_IP1_CAPACITY = 1
BERTH_STORAGE_IP2_CAPACITY = 1

PRODUCTION_TIME = YEAR / 180

LAUNCH_TIME = 4 * HOUR
INTEGRATION_TIME = 1 * HOUR
ASSEMBLY_NC_TOT = 2 * HOUR
COMMISSIONING_TESTING_TIME = 1 * DAY
INSTALLATION_TIME = 40 * HOUR
IAC_HOOKUP_TIME = 12 * HOUR

SHIFTS_PER_TURBINE = 18
TTE_TIME = 2 * HOUR
WTG_COMMISSIONING_TIME = 2 * HOUR

LAUNCH_TIME_WW = 0.5 * HOUR
INTEGRATION_WW = 2 * HOUR
ASSEMBLY_NACELLE_WW = 4 * HOUR
ASSEMBLY_BLADE_WW = 4 * HOUR
INSTALLATION_TIME_WW = 1 * HOUR
IAC_HOOKUP_TIME_WW = 1 * HOUR
TTE_TIME_WW = 0.5 * HOUR
WTG_COMMISSIONING_TIME_WW = 0.5 * HOUR

KNOT_KMH = 1.83
VESSEL_SPEED_EMPTY = 12 * KNOT_KMH / 3.6
VESSEL_SPEED_LOADED = 3 * KNOT_KMH / 3.6
VESSEL_SPEED_CLV = 30 * KNOT_KMH / 3.6

LOCATION_SCENARIOS = {
    "10,10,10": {"manufacturing": shapely.geometry.Point(-4.06788, 57.65),   "wet_storage": shapely.geometry.Point(-3.9, 57.65),       "integration": shapely.geometry.Point(-3.73212, 57.65),  "site": shapely.geometry.Point(-3.564239, 57.65)},

    "0,10,100": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,10,100": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "200,10,100": {"manufacturing": shapely.geometry.Point(-7.408702, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "250,10,100": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "400,10,100": {"manufacturing": shapely.geometry.Point(-10.766311, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "500,10,100": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "700,10,100": {"manufacturing": shapely.geometry.Point(-15.802725, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "750,10,100": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "800,10,100": {"manufacturing": shapely.geometry.Point(-17.481529, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1000,10,100": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1100,10,100": {"manufacturing": shapely.geometry.Point(-22.517943, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1200,10,100": {"manufacturing": shapely.geometry.Point(-24.196748, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1300,10,100": {"manufacturing": shapely.geometry.Point(-25.875552, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1400,10,100": {"manufacturing": shapely.geometry.Point(-27.554357, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1500,10,100": {"manufacturing": shapely.geometry.Point(-29.233161, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},

    "100,10,0": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "100,10,200": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-0.525603, 57.65)},
    "100,10,250": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "100,10,400": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(2.832006, 57.65)},
    "100,10,500": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "100,10,700": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(7.86842, 57.65)},
    "100,10,750": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "100,10,800": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(9.547225, 57.65)},
    "100,10,1000": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "100,10,1100": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(14.583639, 57.65)},
    "100,10,1200": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(16.262443, 57.65)},
    "100,10,1300": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(17.941248, 57.65)},
    "100,10,1400": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(19.620052, 57.65)},
    "100,10,1500": {"manufacturing": shapely.geometry.Point(-5.729897, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(21.298857, 57.65)},

    "100,0,100": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,50,100": {"manufacturing": shapely.geometry.Point(-6.401419, 57.65), "wet_storage": shapely.geometry.Point(-4.722614, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,125,100": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,150,100": {"manufacturing": shapely.geometry.Point(-8.080224, 57.65), "wet_storage": shapely.geometry.Point(-6.401419, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,250,100": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,500,100": {"manufacturing": shapely.geometry.Point(-13.95604, 57.65), "wet_storage": shapely.geometry.Point(-12.277235, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "100,1000,100": {"manufacturing": shapely.geometry.Point(-22.350063, 57.65), "wet_storage": shapely.geometry.Point(-20.671258, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},

    "0,10,0": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "250,10,250": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "500,10,500": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "750,10,750": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "1000,10,1000": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},

    "100,0,0": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "100,0,250": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "100,0,500": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "100,0,750": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "100,0,1000": {"manufacturing": shapely.geometry.Point(-5.562017, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "100,125,0": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "100,125,250": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "100,125,500": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "100,125,750": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "100,125,1000": {"manufacturing": shapely.geometry.Point(-7.660522, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "100,250,0": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "100,250,250": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "100,250,500": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "100,250,750": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "100,250,1000": {"manufacturing": shapely.geometry.Point(-9.759028, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},

    "0,0,0": {"manufacturing": shapely.geometry.Point(-3.883212, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "0,125,0": {"manufacturing": shapely.geometry.Point(-5.981718, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "0,250,0": {"manufacturing": shapely.geometry.Point(-8.080224, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "250,0,250": {"manufacturing": shapely.geometry.Point(-8.080224, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "250,125,250": {"manufacturing": shapely.geometry.Point(-10.178729, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "250,250,250": {"manufacturing": shapely.geometry.Point(-12.277235, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "500,0,500": {"manufacturing": shapely.geometry.Point(-12.277235, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "500,125,500": {"manufacturing": shapely.geometry.Point(-14.375741, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "500,250,500": {"manufacturing": shapely.geometry.Point(-16.474246, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "750,0,750": {"manufacturing": shapely.geometry.Point(-16.474246, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "750,125,750": {"manufacturing": shapely.geometry.Point(-18.572752, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "750,250,750": {"manufacturing": shapely.geometry.Point(-20.671258, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "1000,0,1000": {"manufacturing": shapely.geometry.Point(-20.671258, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "1000,125,1000": {"manufacturing": shapely.geometry.Point(-22.769764, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "1000,250,1000": {"manufacturing": shapely.geometry.Point(-24.86827, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},

    "0,10,30": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.379571, 57.65)},
    "0,10,250": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "0,10,500": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "0,10,750": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "0,10,1000": {"manufacturing": shapely.geometry.Point(-4.051092, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "250,10,0": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "250,10,500": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "250,10,750": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "250,10,1000": {"manufacturing": shapely.geometry.Point(-8.248104, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "500,10,0": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "500,10,250": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "500,10,750": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},
    "500,10,1000": {"manufacturing": shapely.geometry.Point(-12.445115, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "750,10,0": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "750,10,250": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "750,10,500": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "750,10,1000": {"manufacturing": shapely.geometry.Point(-16.642127, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(12.904834, 57.65)},
    "1000,10,0": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-3.883212, 57.65)},
    "1000,10,250": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(0.3138, 57.65)},
    "1000,10,500": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(4.510811, 57.65)},
    "1000,10,750": {"manufacturing": shapely.geometry.Point(-20.839138, 57.65), "wet_storage": shapely.geometry.Point(-4.051092, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(8.707823, 57.65)},

    "0,0,100": {"manufacturing": shapely.geometry.Point(-3.883212, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "0,125,100": {"manufacturing": shapely.geometry.Point(-5.981718, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "0,250,100": {"manufacturing": shapely.geometry.Point(-8.080224, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "250,0,100": {"manufacturing": shapely.geometry.Point(-8.080224, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "250,125,100": {"manufacturing": shapely.geometry.Point(-10.178729, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "250,250,100": {"manufacturing": shapely.geometry.Point(-12.277235, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "500,0,100": {"manufacturing": shapely.geometry.Point(-12.277235, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "500,125,100": {"manufacturing": shapely.geometry.Point(-14.375741, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "500,250,100": {"manufacturing": shapely.geometry.Point(-16.474246, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "750,0,100": {"manufacturing": shapely.geometry.Point(-16.474246, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "750,125,100": {"manufacturing": shapely.geometry.Point(-18.572752, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "750,250,100": {"manufacturing": shapely.geometry.Point(-20.671258, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1000,0,100": {"manufacturing": shapely.geometry.Point(-20.671258, 57.65), "wet_storage": shapely.geometry.Point(-3.883212, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1000,125,100": {"manufacturing": shapely.geometry.Point(-22.769764, 57.65), "wet_storage": shapely.geometry.Point(-5.981718, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},
    "1000,250,100": {"manufacturing": shapely.geometry.Point(-24.86827, 57.65), "wet_storage": shapely.geometry.Point(-8.080224, 57.65), "integration": shapely.geometry.Point(-3.883212, 57.65), "site": shapely.geometry.Point(-2.204407, 57.65)},

    "Hub east": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(-3.463510, 57.65),
        "integration":   shapely.geometry.Point(-2.859140, 57.65),
        "site":          shapely.geometry.Point(0.498470, 57.65),
    },
    "Hub west": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(-3.463510, 57.65),
        "integration":   shapely.geometry.Point(-2.859140, 57.65),
        "site":          shapely.geometry.Point(2.177275, 57.65),
    },
    "Large scale east": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(3.486743, 57.65),
        "integration":   shapely.geometry.Point(4.091113, 57.65),
        "site":          shapely.geometry.Point(7.448723, 57.65),
    },
    "Large scale west": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(3.486743, 57.65),
        "integration":   shapely.geometry.Point(4.091113, 57.65),
        "site":          shapely.geometry.Point(9.127528, 57.65),
    },
    "Central integration east": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(-3.463510, 57.65),
        "integration":   shapely.geometry.Point(-0.391297, 57.65),
        "site":          shapely.geometry.Point(3.721775, 57.65),
    },
    "Central integration west": {
        "manufacturing": shapely.geometry.Point(-4.067880, 57.65),
        "wet_storage":   shapely.geometry.Point(-3.463510, 57.65),
        "integration":   shapely.geometry.Point(-0.391297, 57.65),
        "site":          shapely.geometry.Point(2.177275, 57.65),
    },
}


def get_locations():
    """Node coordinates of the active SCENARIO."""
    if SCENARIO not in LOCATION_SCENARIOS:
        raise ValueError(
            f"Unknown SCENARIO '{SCENARIO}'. "
            f"Choose from: {list(LOCATION_SCENARIOS)}"
        )
    return LOCATION_SCENARIOS[SCENARIO]


def scenario_distances_km(name=None):
    """Geodesic distances d1, d2, d3 (km) of a scenario, as the model sees them."""
    import pyproj

    locs = LOCATION_SCENARIOS[name or SCENARIO]
    geod = pyproj.Geod(ellps="WGS84")
    legs = [("manufacturing", "wet_storage"), ("wet_storage", "integration"),
            ("integration", "site")]
    return tuple(
        geod.inv(locs[a].x, locs[a].y, locs[b].x, locs[b].y)[2] / 1000
        for a, b in legs
    )
