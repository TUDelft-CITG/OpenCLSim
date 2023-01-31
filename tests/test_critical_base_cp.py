""" Tests for openclsim.critical_path.base_cp module """
import datetime as dt

from openclsim.critical_path.base_cp import BaseCP


def test_get_recorded_activity_df_2_barges(simulation_2_barges):
    """Test creation of recorded_activities_df in simulation with 2 barges."""
    TestCP = type(
        "TestCP",
        (BaseCP,),
        {"get_dependency_list": "no need to implement"},
    )
    my_basecp = TestCP(**simulation_2_barges)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 2, 6, 40)
    assert len(recorded_activities_df) == 148
    assert list(recorded_activities_df) == [
        "Activity",
        "ActivityID",
        "SimulationObject",
        "start_time",
        "state",
        "duration",
        "end_time",
        "cp_activity_id",
    ]


def test_get_recorded_activity_df_4_barges(simulation_4_barges):
    """Test creation of recorded_activities_df in simulation with 4 barges."""
    TestCP = type(
        "TestCP",
        (BaseCP,),
        {"get_dependency_list": "no need to implement"},
    )
    my_basecp = TestCP(**simulation_4_barges)
    recorded_activities_df = my_basecp.get_recorded_activity_df()

    assert max(recorded_activities_df.end_time) == dt.datetime(1970, 1, 1, 16, 40)
    assert set(recorded_activities_df.SimulationObject) == {
        "barge_0",
        "barge_1",
        "barge_2",
        "barge_3",
        "from_site",
        "to_site",
        "to_site2",
        "vessel_last",
    }
