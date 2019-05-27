import json
import os
import zipfile

import numpy as np
import pandas as pd
import pytest

from io import StringIO

from digital_twin import server


def run_and_compare_completion_time(config_file, expected_result_file, tmp_path=""):
    with open(config_file) as f:
        config = json.load(f)

    result = server.simulate_from_json(config, tmp_path=tmp_path)

    # checks if result can indeed be turned into json
    result_json = json.dumps(result)

    with open(expected_result_file) as f:
        expected_result = json.load(f)

    np.testing.assert_almost_equal(
        result["completionTime"], expected_result["completionTime"]
    )
    return result


def test_move_activity():
    """Run a basic simulation containing a single move activity and check the output."""
    run_and_compare_completion_time(
        config_file="tests/configs/move_activity.json",
        expected_result_file="tests/results/move_activity_result.json",
    )


def test_multiple_move_activities():
    """Run a basic simulation containing multiple move activities and check the output."""
    run_and_compare_completion_time(
        config_file="tests/configs/multiple_move_activities.json",
        expected_result_file="tests/results/multiple_move_activities_result.json",
    )


def test_single_run_activity():
    run_and_compare_completion_time(
        config_file="tests/configs/single_run_activity.json",
        expected_result_file="tests/results/single_run_activity_result.json",
    )


def test_multiple_single_run_activities():
    run_and_compare_completion_time(
        config_file="tests/configs/multiple_single_run_activities.json",
        expected_result_file="tests/results/multiple_single_run_activities_result.json",
    )


def test_unnecessary_single_run_activity():
    run_and_compare_completion_time(
        config_file="tests/configs/unnecessary_single_run_activity.json",
        expected_result_file="tests/results/unnecessary_single_run_activity_result.json",
    )


def test_conditional_activity():
    run_and_compare_completion_time(
        config_file="tests/configs/conditional_activity.json",
        expected_result_file="tests/results/conditional_activity_result.json",
    )


def test_mover_properties_engine_order():
    """Run a basic simulation containing a single move activity and check the output.
    We give an engine order of 0.8 instead of the default 1.0 used for test_move_activity.
    The completionTime of this test's results should be 25% slower than that of test_move_activity."""
    run_and_compare_completion_time(
        config_file="tests/configs/mover_properties_engine_order.json",
        expected_result_file="tests/results/mover_properties_engine_order_result.json",
    )


def test_mover_properties_load():
    """Run a basic conditional simulation.
    We order to load up to 0.8. Capacity of the ship is 2500 and 10.000 units need to be transported.
    Without the load order this would take 4 trips, it should now take 5."""
    run_and_compare_completion_time(
        config_file="tests/configs/mover_properties_load.json",
        expected_result_file="tests/results/mover_properties_load_result.json",
    )


def test_energy_use():
    """Run a simulation tracking energy use."""
    result = run_and_compare_completion_time(
        config_file="tests/configs/energy_use.json",
        expected_result_file="tests/results/energy_use_result.json",
    )
    hopper_logs = result["equipment"][0]["features"]
    energy_use = 0
    for log_entry in hopper_logs:
        if "Energy use" in log_entry["properties"]["message"]:
            energy_use += log_entry["properties"]["value"]

    np.testing.assert_almost_equal(energy_use, 1791724.970386777)


def test_depth_restriction():
    """Run a simulation including depth restrictions."""
    run_and_compare_completion_time(
        config_file="tests/configs/depth_restriction.json",
        expected_result_file="tests/results/depth_restriction_result.json",
    )


def test_sequential_activity():
    """Runs a simulation with two ships, both ships have their own origin and destination, and each will
    complete a single dredging run. These activities can be done in parallel, but because they are put into
    a sequential activity, we expect them to take place sequentially, i.e., the second ship should not start
    its dredge run until the first ship has completed its run."""
    result = run_and_compare_completion_time(
        config_file="tests/configs/sequential_activity.json",
        expected_result_file="tests/results/sequential_activity_result.json",
    )
    hopper1 = result["equipment"][0]
    assert hopper1["id"] == "hopper1"

    hopper2 = result["equipment"][1]
    assert hopper2["id"] == "hopper2"

    hopper1_done_time = hopper1["features"][-1]["properties"]["time"]
    hopper2_start_time = hopper2["features"][0]["properties"]["time"]
    assert hopper1_done_time <= hopper2_start_time


@pytest.mark.timeout(60)
def test_infinite_loop_detection():
    """Run a simulation that would lead to an infinite loop."""

    run_and_compare_completion_time(
        config_file="tests/configs/infinite_loop.json",
        expected_result_file="tests/results/infinite_loop_result.json",
    )
    assert True  # ensure we get here...


def test_savesim(tmpdir):
    """Runs the same simulation as test_energy_use, but adds saveSimulation: true.
    This should result in the server saving the csv files of the simulation."""

    tmp_path = tmpdir
    run_and_compare_completion_time(
        config_file="tests/configs/savesim.json",
        expected_result_file="tests/results/energy_use_result.json",
        tmp_path=tmp_path,
    )

    config_file_hash = "c1cb76da1ceee6dd4614f94d7ee28cd1"
    expected_files = [
        "activities.csv",
        "dredging_spill.csv",
        "energy_use.csv",
        "equipment.csv",
        "equipment_log.csv",
        "events.csv",
        "locations.csv",
        "simulations.csv",
    ]

    for file in expected_files:
        assert os.path.isfile(
            str(tmp_path) + "/simulations/" + config_file_hash + "_" + file
        )


def test_layered_dike_example():
    """Run a simulation generated by the gui interface based on the layered dike example notebook."""

    run_and_compare_completion_time(
        config_file="tests/configs/layered_dike_example.json",
        expected_result_file="tests/results/layered_dike_example_result.json",
    )


def test_reversed_dependencies():
    """Run the same simulation as done in the test_layered_dike_example test but in this config the activities are
    listed in the reversed order. This causes Simulation to attempt to instantiate them in the reversed order, which
    will fail for the activities containing an is_done condition since the process these activities refer to has not
    been instantiated yet."""
    run_and_compare_completion_time(
        config_file="tests/configs/layered_dike_example_reversed.json",
        expected_result_file="tests/results/layered_dike_example_result.json",
    )


def test_circular_dependency():
    """Run a simulation which contains a circular dependency. The configuration defines two activities, which both
    contain an is_done condition for the other activity. This makes it impossible to instantiate processes for these
    activities, because to create an event for these conditions, the other activity's process must already be
    instantiated. The server should detect this situation and throw an error."""
    with pytest.raises(ValueError) as err:
        run_and_compare_completion_time(
            config_file="tests/configs/circular_dependency.json",
            expected_result_file="",  # does not matter, error raised before this is used to check result
        )

    assert (
        "Unable to instantiate activities act_1, act_2; their is_done conditions form a circle."
        in str(err)
    )
