from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

import simpy
from digital_twin import model
import datetime
import time

import json
import hashlib

app = Flask(__name__)
CORS(app)

@app.route("/")
def main():
    return jsonify(dict(message="Basic Digital Twin Server"))


@app.route("/simulate", methods=['POST'])
def simulate():
    """run a simulation"""
    if not request.is_json:
        abort(400, description="content type should be json")
        return

    config = request.get_json(force=True)

    try:
        simulation_result = simulate_from_json(config)
    except ValueError as valerr:
        abort(400, description=str(valerr))
        return
    except Exception as e:
        abort(500, description=str(e))
        return

    return jsonify(simulation_result)


def simulate_from_json(config, tmp_path=""):
    """Create a simulation and run it, based on a json input file.
    The optional tmp_path parameter should only be used for unit tests."""
    if "initialTime" in config:
        simulation_start = datetime.datetime.fromtimestamp(config["initialTime"])
    else:
        simulation_start = datetime.datetime.now()
    env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))

    simulation = model.Simulation(
        env=env,
        name="server simulation",
        sites=config["sites"],
        equipment=config["equipment"],
        activities=config["activities"]
    )
    env.run()

    result = simulation.get_logging()
    result["completionTime"] = env.now

    if "saveSimulation" in config and config["saveSimulation"]:
        save_simulation(config, simulation, tmp_path=tmp_path)

    return result


def save_simulation(config, simulation, tmp_path=""):
    """Save the given simulation. The config is used to produce an md5 hash of its text representation.
    This hash is used as a prefix for the files which are written. This ensures that simulations with the same config
    are written to the same files (although it is not a completely foolproof method, for example changing an equipment
    or location name, does not alter the simulation result, but does alter the config file).
    The optional tmp_path parameter should only be used for unit tests."""

    config_text = json.dumps(config, sort_keys=True).encode("utf-8")
    hash = hashlib.md5(config_text).hexdigest()
    file_prefix = hash + '_'

    path = str(tmp_path)
    if len(path) != 0 and str(path)[-1] != "/":
        path += "/"
    simulation.save_logs(path + "simulations/", file_prefix)
