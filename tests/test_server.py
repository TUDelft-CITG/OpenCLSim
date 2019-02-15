import json
from digital_twin import server


def test_simulation():
      """Run a basic simulation and check the output."""
    with open('tests/configs/basic_simulation.json') as f:
        config = json.load(f)

    result = server.simulate_from_json(config)

    # checks if result can indeed be turned into json
    result_json = json.dumps(result)

    with open('tests/results/basic_simulation_result.json') as f:
        expected_result = f.read()

    assert result_json == expected_result
