import datetime
import time

from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

import matplotlib
# make sure we use Agg for offscreen rendering
matplotlib.use('Agg')

import simpy

from digital_twin import model, core, plot

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

    json = request.get_json(force=True)

    try:
        simulation_result = simulate_from_json(json)
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

def simulate_from_json(json):
    """Create a simulation and run it, based on a json input file"""
    if "initialTime" in json:
        simulation_start = datetime.datetime.fromtimestamp(json["initialTime"])
    else:
        simulation_start = datetime.datetime.now()
    env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))

    simulation = model.Simulation(
        env=env,
        name="server simulation",
        sites=json["sites"],
        equipment=json["equipment"],
        activities=json["activities"]
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
