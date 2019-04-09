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
matplotlib.use('Agg')

import simpy
from digital_twin import model
from digital_twin import savesim
from digital_twin import core
from digital_twin import plot

import datetime
import os
import time

from digital_twin import model, core, plot

import pandas as pd
import glob

import pathlib
import urllib.parse

import json
import hashlib

root_folder = pathlib.Path(__file__).parent.parent
static_folder = root_folder / 'static'
assert static_folder.exists(), "Make sure you run the server from the static directory. {} does not exist".format(static_folder)
app = Flask(__name__, static_folder=str(static_folder))
CORS(app)


@app.route("/")
def main():
    return jsonify(dict(message="Basic Digital Twin Server"))


@app.route("/csv")
def csv():
    print(dir(request), request, request.url, request.base_url, request.host_url)
    paths = [
        urllib.parse.urljoin(
            request.host_url,
            str(x)
        )
        for x
        in static_folder.relative_to(root_folder).glob('**/*.csv')
    ]
    print(paths, static_folder)
    df = pd.DataFrame(data={"paths": paths})
    csv = df.to_csv(index=False)
    resp = make_response(csv)
    resp.headers['Content-Type'] = "text/csv"
    return resp


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

@app.route("/plot")
def demo_plot():
    """demo plot"""
    fig = plot.demo_plot()
    return plot.fig2response(fig)

@app.route("/planning", methods=['POST'])
def planning_plot():
    """return a planning"""
    if not request.is_json:
        abort(400, description="content type should be json")
        return

    json = request.get_json(force=True)

    try:
        simulation_planning = equipment_plot_from_json(json)
    except ValueError as valerr:
        abort(400, description=str(valerr))
        return
    except Exception as e:
        abort(500, description=str(e))
        return

    return simulation_planning

def simulate_from_json(config, tmp_path="static"):
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
    file_prefix = hash + '_'

    path = str(tmp_path)
    if len(path) != 0 and str(path)[-1] != "/":
        path += "/"
    # TODO: use pathlib
    path += "simulations/"
    os.makedirs(path, exist_ok=True)  # create the simulations directory if it does not yet exist
    savesim.save_logs(simulation, path, file_prefix)

def equipment_plot_from_json(json):
    """Create a Gantt chart, based on a json input file"""

    j = json.loads(str(json))

    vessels = []
    for item in j['equipment']:
        if item['features']:
            vessel = type('Vessel', (core.Identifiable, core.Log), {})
            vessel = vessel(**{"env": None, "name": item['id']})

            for feature in item['features']:
                vessel.log_entry(log = feature['properties']['message'],
                                 t = feature['properties']['time'],
                                 value = feature['properties']['value'],
                                 geometry_log = feature['geometry']['coordinates'])


            vessels.append(vessel)

    activities = ['loading', 'unloading', 'sailing filled', 'sailing empty']
    colors = {0:'rgb(55,126,184)', 1:'rgb(255,150,0)', 2:'rgb(98, 192, 122)', 3:'rgb(98, 141, 122)'}

    plot.vessel_planning(vessels, activities, colors)


    return plot.vessel_planning(vessels, activities, colors, static = True)
