import json
import logging

from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from flask import send_file
from flask import send_from_directory
from flask import make_response
from flask_cors import CORS

import matplotlib

# make sure we use Agg for offscreen rendering
matplotlib.use("Agg")

import simpy
from openclsim import model
from openclsim import savesim
from openclsim import core
from openclsim import plot

import datetime
import functools
import os
import time

import pandas as pd
import glob

import pathlib
import urllib.parse

import json
import hashlib

root_folder = pathlib.Path(__file__).parent.parent
static_folder = root_folder / "static"
assert (
    static_folder.exists()
), "Make sure you run the server from the static directory. {} does not exist".format(
    static_folder
)
app = Flask(__name__, static_folder=str(static_folder))
CORS(app)

logger = logging.getLogger(__name__)


@app.route("/")
def main():
    return jsonify(dict(message="Basic Digital Twin Server"))


@app.route("/csv")
def csv():
    print(dir(request), request, request.url, request.base_url, request.host_url)
    paths = [
        urllib.parse.urljoin(request.host_url, str(x))
        for x in static_folder.relative_to(root_folder).glob("**/*.csv")
    ]
    print(paths, static_folder)
    df = pd.DataFrame(data={"paths": paths})
    csv = df.to_csv(index=False)
    resp = make_response(csv)
    resp.headers["Content-Type"] = "text/csv"
    return resp


@app.route("/simulate", methods=["POST"])
def simulate():
    """run a simulation"""
    if not request.is_json:
        abort(400, description="content type should be json")
        return

    config = request.get_json(force=True)

    try:
        simulation_result = simulate_from_json(config)
    except ValueError as valerr:
        return jsonify({"error": str(valerr)})
    except RuntimeError as runerr:
        return jsonify({"error": str(runerr)})
    except Exception as e:
        abort(500, description=str(e))
        return

    return jsonify(simulation_result)


@app.route("/plot")
def demo_plot():
    """demo plot"""

    # Gantt + Spill + CO2

    fig = plot.demo_plot()
    return plot.fig2response(fig)


@app.route("/energy_plot", methods=["POST"])
def energy_plot():
    """return a plot with the cumulative energy use"""
    if not request.is_json:
        raise ValueError("content type should be json")

    config = request.get_json(force=True)

    try:
        energy_use = energy_use_plot_from_json(config)
    except ValueError as valerr:
        abort(400, description=str(valerr))
        return
    except Exception as e:
        abort(500, description=str(e))
        return

    return plot.fig2response(energy_use)


@app.route("/equipment_plot", methods=["POST"])
def equipment_plot():
    """return a planning"""
    if not request.is_json:
        abort(400, description="content type should be json")
        return

    config = request.get_json(force=True)

    try:
        equipment_plot = equipment_plot_from_json(config)
    except ValueError as valerr:
        abort(400, description=str(valerr))
        return
    except RuntimeError as runerr:
        abort(400, description=str(runerr))
        return
    except Exception as e:
        abort(500, description=str(e))
        return

    return plot.fig2response(equipment_plot)


def update_end_time(event, env):
    event.end_time = env.now


def interrupt_processes(event, activities, env):
    for activity in activities:
        process = activity["process"]
        if not process.processed:
            process.interrupt()
            activity["activity_log"].log_entry(
                "interrupted by 100 year timeout",
                env.now,
                -1,
                None,
                activity["activity_log"].id,
            )


def simulate_from_json(config, tmp_path="static"):
    """Create a simulation and run it, based on a json input file.
    The optional tmp_path parameter should only be used for unit tests."""

    if "initialTime" in config:
        try:
            simulation_start = datetime.datetime.fromtimestamp(config["initialTime"])
        except OSError:
            # on windows in certain python versions 0 is not a good start date
            simulation_start = datetime.datetime(2000, 1, 1)
    else:
        simulation_start = datetime.datetime.now()
    env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))

    simulation = model.Simulation(
        env=env,
        name="server simulation",
        sites=config["sites"],
        equipment=config["equipment"],
        activities=config["activities"],
    )
    processes = [activity["process"] for activity in simulation.activities.values()]

    for process in processes:
        process.end_time = None
        process.callbacks.append(functools.partial(update_end_time, env=env))

    timeout_100years = env.timeout(100 * 365 * 24 * 3600)
    timeout_100years.callbacks.append(
        functools.partial(
            interrupt_processes, activities=simulation.activities.values(), env=env
        )
    )

    try:
        env.run()
        completion_time = max(process.end_time for process in processes)
    except simpy.Interrupt:
        completion_time = env.now

    result = simulation.get_logging()
    result["completionTime"] = completion_time

    costs = 0
    for piece in simulation.equipment:

        if isinstance(simulation.equipment[piece], core.HasCosts):
            costs += simulation.equipment[piece].cost

    result["completionCost"] = costs

    if "saveSimulation" in config and config["saveSimulation"]:
        save_simulation(config, simulation, tmp_path=tmp_path)

    return result


def save_simulation(config, simulation, tmp_path=""):
    """Save the given simulation. The config is used to produce an md5 hash of its text representation.
    This hash is used as a prefix for the files which are written. This ensures that simulations with the same config
    are written to the same files (although it is not a completely foolproof method, for example changing an equipment
    or location name, does not alter the simulation result, but does alter the config file).
    The optional tmp_path parameter should only be used for unit tests."""

    # TODO: replace traversing static_folder pathlib path
    config_text = json.dumps(config, sort_keys=True).encode("utf-8")
    hash = hashlib.md5(config_text).hexdigest()
    file_prefix = hash + "_"

    path = str(tmp_path)
    if len(path) != 0 and str(path)[-1] != "/":
        path += "/"
    # TODO: use pathlib
    path += "simulations/"
    os.makedirs(
        path, exist_ok=True
    )  # create the simulations directory if it does not yet exist
    savesim.save_logs(simulation, path, file_prefix)


def energy_use_plot_from_json(jsonFile):
    """Create a Gantt chart, based on a json input file"""

    vessels = []
    for item in jsonFile["equipment"]:
        if item["features"]:
            vessel = type("Vessel", (core.Identifiable, core.Log), {})
            vessel = vessel(**{"env": None, "name": item["id"]})

            for feature in item["features"]:
                vessel.log_entry(
                    log=feature["properties"]["message"],
                    t=feature["properties"]["time"],
                    value=feature["properties"]["value"],
                    geometry_log=feature["geometry"]["coordinates"],
                    ActivityID=None,
                )

            vessels.append(vessel)

    return plot.energy_use_time(vessels, web=True)


def equipment_plot_from_json(jsonFile):
    """Create a Gantt chart, based on a json input file"""

    vessels = []
    for item in jsonFile["equipment"]:
        if item["features"]:
            vessel = type("Vessel", (core.Identifiable, core.Log), {})
            vessel = vessel(**{"env": None, "name": item["id"]})

            for feature in item["features"]:
                vessel.log_entry(
                    log=feature["properties"]["message"],
                    t=feature["properties"]["time"],
                    value=feature["properties"]["value"],
                    geometry_log=feature["geometry"]["coordinates"],
                    ActivityID=None,
                )

            vessels.append(vessel)

    return plot.equipment_plot_json(vessels, web=True)
