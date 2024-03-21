import datetime

import pytest
import shapely
import simpy

import openclsim.core


@pytest.fixture
def env():
    return simpy.Environment()


def test_log_entry_v0(env):
    log = openclsim.core.Log(env=env)

    geometry = shapely.Point(0, 0)
    log.log_entry_v0(log="test", t=0, value="test", geometry_log=geometry)

    expected = {
        "Message": "test",
        "Timestamp": datetime.datetime(1970, 1, 1, 1, 0),
        "Value": "test",
        "Geometry": geometry,
    }
    assert log.logbook == [expected]


def test_log_entry_v1(env):
    log = openclsim.core.Log(env=env)
    log_state = openclsim.core.LogState.UNKNOWN
    log.log_entry_v1(t=0, activity_id="abc", activity_state=log_state)
    assert log.logbook == [
        {
            "Timestamp": datetime.datetime(1970, 1, 1, 0, 0),
            "ActivityID": "abc",
            "ActivityLabel": {},
            "ActivityState": "UNKNOWN",
            "ObjectState": {},
        }
    ]


def test_log_property(env, recwarn):
    log = openclsim.core.Log(env=env)
    log_state = openclsim.core.LogState.UNKNOWN
    log.log_entry_v1(t=0, activity_id="abc", activity_state=log_state)

    n_warnings_before = len(recwarn)

    assert log.log == {
        "Timestamp": [datetime.datetime(1970, 1, 1, 0, 0)],
        "ActivityID": ["abc"],
        "ActivityLabel": [{}],
        "ActivityState": ["UNKNOWN"],
        "ObjectState": [{}],
    }
    n_warnings_after = len(recwarn)
    n_warnings = n_warnings_after - n_warnings_before

    assert n_warnings == 0, "no warnings expected during get of .log property"
