from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

import simpy
from digital_twin import model
import datetime
import time

app = Flask(__name__)
CORS(app)

@app.route("/")
def main():
    return jsonify(dict(message="Basic Digital Twin Server"))


@app.route("/simulate", methods=['POST'])
def simulate():
    """run a simulation"""
    if not request.is_json:
        return "content type should be json!"
    json = request.get_json(force=True)

    return jsonify(simulate_from_json(json))


def simulate_from_json(json):
    if "initial_time" in json:
        simulation_start = datetime.datetime.fromtimestamp(json["initial_time"])
    else:
        simulation_start = datetime.datetime.now()
    env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))

    simulation = model.Simulation(
        env=env,
        name="server simulation",
        sites=json["sites"],
        equipment=json["equipment"],
        activities=json["activities"],
        decision_code=""  # todo add option to configure decision_code (blockly code) through json
    )
    env.run()

    result = dict(
        completion_time=env.now,
        logging=simulation.get_logging()
    )

    return result
