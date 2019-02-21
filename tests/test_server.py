import json

import numpy as np

from digital_twin import server


def run_and_compare_output(config_file, expected_result_file):
    with open(config_file) as f:
        config = json.load(f)

    result = server.simulate_from_json(config)

    # checks if result can indeed be turned into json
    result_json = json.dumps(result)

    with open(expected_result_file) as f:
        expected_result = json.load(f)

    np.testing.assert_almost_equal(result["completionTime"], expected_result["completionTime"])


def test_move_activity():
    """Run a basic simulation containing a single move activity and check the output."""
    run_and_compare_output(
        config_file='tests/configs/move_activity.json',
        expected_result_file='tests/results/move_activity_result.json'
    )


def test_multiple_move_activities():
    """Run a basic simulation containing multiple move activities and check the output."""
    run_and_compare_output(
        config_file='tests/configs/multiple_move_activities.json',
        expected_result_file='tests/results/multiple_move_activities_result.json'
    )


def test_single_run_activity():
    run_and_compare_output(
        config_file='tests/configs/single_run_activity.json',
        expected_result_file='tests/results/single_run_activity_result.json'
    )


def test_multiple_single_run_activities():
    run_and_compare_output(
        config_file='tests/configs/multiple_single_run_activities.json',
        expected_result_file='tests/results/multiple_single_run_activities_result.json'
    )


def test_conditional_activity():
    run_and_compare_output(
        config_file='tests/configs/conditional_activity.json',
        expected_result_file='tests/results/conditional_activity_result.json'
    )


def test_mover_options_engine_order():
    """Run a basic simulation containing a single move activity and check the output.
    We give an engine order of 0.8 instead of the default 1.0 used for test_move_activity.
    The completionTime of this test's results should be 25% slower than that of test_move_activity."""
    run_and_compare_output(
        config_file='tests/configs/mover_options_engine_order.json',
        expected_result_file='tests/results/mover_options_engine_order_result.json'
   )


def test_mover_options_load():
    """Run a basic conditional simulation.
    We order to load up to 0.8. Capacity of the ship is 2500 and 10.000 units need to be transported.
    Without the load order this would take 4 trips, it should now take 5."""
    run_and_compare_output(
        config_file='tests/configs/mover_options_load.json',
        expected_result_file='tests/results/mover_options_load_result.json'
    )
