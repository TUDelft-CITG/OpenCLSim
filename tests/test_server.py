import json
from digital_twin import server


def run_and_compare_output(config_file, expected_result_file):
    with open(config_file) as f:
        config = json.load(f)

    result = server.simulate_from_json(config)

    # checks if result can indeed be turned into json
    result_json = json.dumps(result)

    with open(expected_result_file) as f:
        expected_result = f.read()

    assert result_json == expected_result


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
