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

    np.testing.assert_almost_equal(result["completionTime"], expected_result["completionTime"])
    return result


def test_move_activity():
    """Run a basic simulation containing a single move activity and check the output."""
    run_and_compare_completion_time(
        config_file='tests/configs/move_activity.json',
        expected_result_file='tests/results/move_activity_result.json'
    )


def test_multiple_move_activities():
    """Run a basic simulation containing multiple move activities and check the output."""
    run_and_compare_completion_time(
        config_file='tests/configs/multiple_move_activities.json',
        expected_result_file='tests/results/multiple_move_activities_result.json'
    )


def test_single_run_activity():
    run_and_compare_completion_time(
        config_file='tests/configs/single_run_activity.json',
        expected_result_file='tests/results/single_run_activity_result.json'
    )


def test_multiple_single_run_activities():
    run_and_compare_completion_time(
        config_file='tests/configs/multiple_single_run_activities.json',
        expected_result_file='tests/results/multiple_single_run_activities_result.json'
    )


def test_conditional_activity():
    run_and_compare_completion_time(
        config_file='tests/configs/conditional_activity.json',
        expected_result_file='tests/results/conditional_activity_result.json'
    )


def test_mover_properties_engine_order():
    """Run a basic simulation containing a single move activity and check the output.
    We give an engine order of 0.8 instead of the default 1.0 used for test_move_activity.
    The completionTime of this test's results should be 25% slower than that of test_move_activity."""
    run_and_compare_completion_time(
        config_file='tests/configs/mover_properties_engine_order.json',
        expected_result_file='tests/results/mover_properties_engine_order_result.json'
   )


def test_mover_properties_load():
    """Run a basic conditional simulation.
    We order to load up to 0.8. Capacity of the ship is 2500 and 10.000 units need to be transported.
    Without the load order this would take 4 trips, it should now take 5."""
    run_and_compare_completion_time(
        config_file='tests/configs/mover_properties_load.json',
        expected_result_file='tests/results/mover_properties_load_result.json'
    )


def test_energy_use():
    """Run a simulation tracking energy use."""
    result = run_and_compare_completion_time(
        config_file='tests/configs/energy_use.json',
        expected_result_file='tests/results/energy_use_result.json'
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
        config_file='tests/configs/depth_restriction.json',
        expected_result_file='tests/results/depth_restriction_result.json'
    )


def test_sequential_activity():
    """Runs a simulation with two ships, both ships have their own origin and destination, and each will
    complete a single dredging run. These activities can be done in parallel, but because they are put into
    a sequential activity, we expect them to take place sequentially, i.e., the second ship should not start
    its dredge run until the first ship has completed its run."""
    result = run_and_compare_completion_time(
        config_file='tests/configs/sequential_activity.json',
        expected_result_file='tests/results/sequential_activity_result.json'
    )
    hopper1 = result['equipment'][0]
    assert hopper1['id'] == 'hopper1'

    hopper2 = result['equipment'][1]
    assert hopper2['id'] == 'hopper2'

    hopper1_done_time = hopper1['features'][-1]['properties']['time']
    hopper2_start_time = hopper2['features'][0]['properties']['time']
    assert hopper1_done_time <= hopper2_start_time


@pytest.mark.timeout(60)
def test_infinite_loop_detection():
    """Run a simulation that would lead to an infinite loop."""
    run_and_compare_completion_time(
        config_file='tests/configs/infinite_loop.json',
        expected_result_file='tests/results/infinite_loop_result.json'
    )
    assert True  # ensure we get here...


def test_savesim(tmp_path):
    """Runs the same simulation as test_energy_use, but adds saveSimulation: true.
    This should result in the server saving the csv files of the simulation."""
    run_and_compare_completion_time(
        config_file='tests/configs/savesim.json',
        expected_result_file='tests/results/energy_use_result.json',
        tmp_path=tmp_path
    )

    config_file_hash = '47fabd7fff7f1fa8a20af93b8f0b6971'
    expected_files = [
        'activities.csv',
        'dredging_spill.csv',
        'energy_use.csv',
        'equipment.csv',
        'equipment_log.csv',
        'events.csv',
        'locations.csv',
        'simulations.csv'
    ]

    for file in expected_files:
        assert os.path.isfile(str(tmp_path) + '/simulations/' + config_file_hash + '_' + file)


def test_zipfile(tmp_path):
    """Runs two simulations which should be stored in separate files (running one of them twice to check that the
    results are indeed overwritten by the second run) and checks if all results are included in the created zipfile"""
    run_and_compare_completion_time(
        config_file='tests/configs/savesim.json',
        expected_result_file='tests/results/energy_use_result.json',
        tmp_path=tmp_path
    )
    run_and_compare_completion_time(
        config_file='tests/configs/savesim2.json',
        expected_result_file='tests/results/conditional_activity_result.json',
        tmp_path=tmp_path
    )
    run_and_compare_completion_time(
        config_file='tests/configs/savesim.json',
        expected_result_file='tests/results/energy_use_result.json',
        tmp_path=tmp_path
    )

    results_dir = str(tmp_path) + '/simulations/'
    server.create_zipfile(directory=results_dir, filename="results.zip")
    file = results_dir + "results.zip"
    assert os.path.isfile(file)
    assert zipfile.is_zipfile(file)

    zipf = zipfile.ZipFile(file, 'r')
    files = zipf.namelist()
    assert len(files) == 8

    expected_files = [
        'activities',
        'dredging_spill',
        'energy_use',
        'equipment',
        'equipment_log',
        'events',
        'locations',
        'simulations'
    ]

    # the uuids are generated randomly each time this test is run, so we can't check on the ID column
    # todo possibly add checks on the other content of the other columns
    for file in files:
        content = zipf.read(file)
        si = StringIO(content.decode("utf-8"))
        df = pd.read_csv(si)
        if file.endswith('activities.csv') or file.endswith('equipment.csv') or file.endswith('simulations.csv'):
            assert len(df) == 2
        if file.endswith('dredging_spill.csv'):
            assert len(df) == 0
        if file.endswith('energy_use.csv'):
            assert len(df) == 32
        if file.endswith('equipment_log.csv'):
            assert len(df) == 48
        if file.endswith('events.csv'):
            assert len(df) == 8
        if file.endswith('locations.csv'):
            assert len(df) == 6



