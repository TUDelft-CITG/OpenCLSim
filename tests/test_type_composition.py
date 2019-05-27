import simpy

import pytest
import datetime
import time

from digital_twin import core


@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env


def test_compose_crane(env):
    """Create a new type crane, based on existing components"""
    Crane = type("Crane", (core.Identifiable, core.HasContainer), {})
    Crane(name="my crane", env=env, capacity=3)
