import json
from digital_twin import server


def test_simulation():
    with open('tests/configs/basic_simulation.json') as f:
        config = json.load(f)

    result = server.simulate_from_json(config)

    # checks if result can indeed be turned into json
    result_json = json.dumps(result)

    i = 0
    # todo add actual checks on if simulation ran as expected
