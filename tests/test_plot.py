#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `digital_twin` package."""

import pytest
import simpy
import shapely.geometry
import logging
import datetime
import time
import json
import numpy as np

import matplotlib
from matplotlib.testing.decorators import image_comparison
import matplotlib.pyplot as plt

from click.testing import CliRunner

from digital_twin import core
from digital_twin import plot
from digital_twin import cli

logger = logging.getLogger(__name__)

@image_comparison(baseline_images=['energy_use'], extensions=['png'])
def test_energy_use_plot():
    
    class vessel():
        def __init__(self, log, name):
            self.log = log
            self.name = name
    
    with open('tests/baseline_images/energy_use.json') as f:
        data = json.load(f)
    
    vessel = vessel(data, "Test vessel")

    plot.energy_use(vessel, testing = True)