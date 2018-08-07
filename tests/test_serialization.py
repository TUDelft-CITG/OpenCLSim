import json

import simpy
import pytest

from digital_twin import core

@pytest.fixture
def env():
    return simpy.Environment()


def test_store_crane(env):
    """Create a new type crane, based on existing components"""
    Crane = type("Crane", (core.Identifiable, core.HasContainer), {})
    crane = Crane(name='my crane', env=env, capacity=3)
    assert crane.container.capacity == 3
    txt = core.serialize(crane)
    data = json.loads(txt)
    print(data)
    crane2 = Crane(env=env, **data)
    assert crane2.container.capacity == 3
