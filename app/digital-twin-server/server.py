from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__)

equipment_data = {
    'S1': {
        'name': 'EGG123',
        'type': 'Transport barge',
        'speed loaded': 6.5,
        'tonnage': 2601,
        'tags': ['mover']
    },
    'S2': {
        'name': 'Boaty McBoatStone',
        'type': 'Multi purpose support vessel',
        'speed loaded': 7.0,
        'tonnage': 1824,
        'capacity': 10.3,
        'tags': ['loader', 'mover']
    },
    'C1': {
        'name': 'Loady McLoader',
        'type': 'Simple Loading Crane',
        'capacity': 13.2
    },
    'C2': {
        'name': 'Unloady McUnloader',
        'type': 'Simple Loading Crane',
        'capacity': 12.1
    }
}

@app.route("/")
def hello():
    return jsonify(dict(message="Basic Digital Twin Server"))

@app.route("/equipment")
def equipment_list():
    return jsonify(list(equipment_data.keys()))

@app.route("/equipment/<id>")
def equipment(id):
    return jsonify(equipment_data[id])

@app.route("/simulate", methods=['POST'])
def simulate():
    if not request.is_json:
        return "content type should be json!"
    json = request.get_json(force=True)
    return jsonify(json)

@app.route("/test", methods=['POST'])
def json_test():
    return "JSON!" if request.is_json else ":("
