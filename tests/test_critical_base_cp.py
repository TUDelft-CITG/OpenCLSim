"""
Tests for openclsim.critical_path.base_cp module.
Tests the method 'get_recorded_activity_df' for a number of simulations.
"""
import datetime as dt

from openclsim.critical_path.base_cp import BaseCP

# define class that inherits from BaseCP for testing purposes only
TestCP = type(
    "TestCP",
    (BaseCP,),
    {"get_dependency_list": None},
)


def test_get_recorded_activity_df_2_barges(simulation_2_barges):
    """Test creation of recorded_activities_df in simulation with 2 barges."""
    my_basecp = TestCP(**simulation_2_barges)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 2, 6, 40)
    assert len(recorded_activities_df) == 402, "402 (shared) activities recorded"
    assert (
        len(recorded_activities_df.cp_activity_id.unique()) == 254
    ), "254 unique activities"
    assert list(recorded_activities_df.columns) == [
        "ActivityID",
        "Activity",
        "SimulationObject",
        "start_time",
        "end_time",
        "duration",
        "state",
        "cp_activity_id",
    ]


def test_get_recorded_activity_df_4_barges(simulation_4_barges):
    """Test creation of recorded_activities_df in simulation with 4 barges."""
    my_basecp = TestCP(**simulation_4_barges)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 1, 16, 40)
    assert recorded_activities_df["SimulationObject"].value_counts().to_dict() == {
        "Activity": 256,
        "barge_1": 25,
        "barge_0": 25,
        "barge_3": 25,
        "barge_2": 25,
        "from_site": 21,
        "to_site": 20,
        "vessel_last": 6,
        "to_site2": 1,
    }


def test_get_recorded_activity_df_2_barges_storm(simulation_2_barges_storm):
    """
    Test creation of recorded_activities_df in simulation
     with 2 barges and the wether delay plugin.
    """
    my_basecp = TestCP(**simulation_2_barges_storm)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 2, 9, 8, 55)
    assert len(recorded_activities_df) == 408, "408 (shared) activities recorded"
    assert (
        len(recorded_activities_df.cp_activity_id.unique()) == 260
    ), "260 unique activities"
    assert list(recorded_activities_df.columns) == [
        "ActivityID",
        "Activity",
        "SimulationObject",
        "start_time",
        "end_time",
        "duration",
        "state",
        "cp_activity_id",
    ]


def test_get_recorded_activity_startevent(simulation_2_barges_start):
    """
    Test creation of recorded_activities_df in simulation
    with 2 barges and the start event.
    """
    my_basecp = TestCP(**simulation_2_barges_start)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 2, 7, 40)
    assert len(recorded_activities_df) == 404, "404 (shared) activities recorded"
    assert (
        len(recorded_activities_df.cp_activity_id.unique()) == 256
    ), "260 unique activities"
