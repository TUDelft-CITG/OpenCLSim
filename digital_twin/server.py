import json
import logging

from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

import simpy
from digital_twin import model, core, plot
import datetime
import time

app = Flask(__name__)
CORS(app)

logger = logging.getLogger(__name__)

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


    simulation_result = simulate_from_json(config)

    return jsonify(simulation_result)

@app.route("/planning", methods=['POST'])
def planning_plot():
    """return a planning"""
    if not request.is_json:
        raise ValueError("content type should be json")

    planning = request.get_json(force=True)

    logger.error('got planning >>>%s<<<', planning)
    simulation_planning = equipment_plot(planning)

    return simulation_planning

def simulate_from_json(config):
    """Create a simulation and run it, based on a json input file"""
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

    return result

def equipment_plot(equipment):
    """Create a Gantt chart, based on a json input file"""

    j = equipment

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
