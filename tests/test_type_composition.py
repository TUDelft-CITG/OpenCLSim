import simpy

import pytest

from digital_twin import core


@pytest.fixture
def env():
    return simpy.Environment()


def test_compose_crane(env):
    """Create a new type crane, based on existing components"""
    Crane = type("Crane", (core.Identifiable, core.HasContainer), {})
    Crane(name='my crane', env=env, capacity=3)
