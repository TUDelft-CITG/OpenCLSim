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


def test_store_stockpile(env):
    """Create a new type crane, based on existing components"""
    Stockpile = type("Stockpile", (core.Identifiable, core.HasResource), {})
    stockpile = Stockpile(name='my stockpile', env=env, nr_resources=3)
    assert stockpile.resource.capacity == 3
    txt = core.serialize(stockpile)
    data = json.loads(txt)
    print(data)
    stockpile2 = Stockpile(env=env, **data)
    assert stockpile2.resource.capacity == 3
