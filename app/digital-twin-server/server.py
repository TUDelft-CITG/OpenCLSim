from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

import simpy
from digital_twin import core
from digital_twin import model
import shapely.geometry
import pint

app = Flask(__name__)
CORS(app)


EQUIPMENT_DB = [
    {
        'id': 'S1',
        'name': 'EGG123',
        'type': 'Transport barge',
        'img': 'https://upload.wikimedia.org/wikipedia/commons/6/60/Barge_%C3%A0_charbon.jpg',
        'properties': {
            'speed loaded': 6.5,
            'tonnage': 2601
        },
        'tags': ['mover']
    },
    {
        'id': 'S2',
        'name': 'Boaty McBoatStone',
        'type': 'Multi purpose support vessel',
        'img': 'https://c1.staticflickr.com/8/7248/13806607764_411823213a_b.jpg',
        'properties': {
            'speed loaded': 7.0,
            'tonnage': 1824,
            'capacity': 10.3
        },
        'tags': ['loader', 'mover']
    },
    {
        'id': 'C1',
        'name': 'Loady McLoader',
        'type': 'Simple Loading Crane',
        'img': 'https://upload.wikimedia.org/wikipedia/commons/2/24/Dock_Crane%2C_Belfast_%286%29_-_geograph.org.uk_-_878924.jpg',
        'properties': {
            'capacity': 13.2
        },
       'tags': ['loader']


    },
    {
        'id': 'C2',
        'name': 'Unloady McUnloader',
        'type': 'Simple Loading Crane',
        'img': 'https://upload.wikimedia.org/wikipedia/commons/2/24/Dock_Crane%2C_Belfast_%286%29_-_geograph.org.uk_-_878924.jpg',
        'properties': {
            'capacity': 12.1
        },
        'tags': ['unloader']


    }
]


type_to_mixins_mapping = {
    'Transport barge': (
        core.Identifiable,
        core.Log,
        core.ContainerDependentMovable,
        core.HasResource,
        core.HasFuel
    ),
    'Multi purpose support vessel': (
        core.Identifiable,
        core.Log,
        core.ContainerDependentMovable,
        core.Processor,
        core.HasResource,
        core.HasFuel
    ),
    'Simple Loading Crane': (
        core.Identifiable,
        core.Log,
        core.Processor,
        core.HasResource
    )
}

Site = type(
    "Site", (
        core.Identifiable,
        core.Log,
        core.Locatable,
        core.HasContainer,
        core.HasResource
    ),
    {}
)

ureg = pint.UnitRegistry()


@app.route("/")
def main():
    return jsonify(dict(message="Basic Digital Twin Server"))


@app.route("/equipment")
def equipment_list():
    """return list of equipment ids """
    return jsonify(EQUIPMENT_DB)


@app.route("/equipment/<id>")
def equipment(id):
    """return equipment"""
    return jsonify(EQUIPMENT_DB[id])


@app.route("/simulate", methods=['POST'])
def simulate():
    """run a simulation"""
    if not request.is_json:
        return "content type should be json!"
    json = request.get_json(force=True)

    origins_data = json["origins"]
    destinations_data = json["destination"]
    equipment_data = json["equipment"]

    env = simpy.Environment()

    origins = []
    for origin_data in origins_data["features"]:
        site = create_site(origin_data, env)
        site.container.put(site.container.capacity)  # fill the origins
        origins.append(site)

    destinations = []
    for destination_data in destinations_data["features"]:
        site = create_site(destination_data, env)
        destinations.append(site)

    print('equipment', equipment_data)
    equipment = {}
    for equipment_json in equipment_data:
        equipment_object = create_equipment(equipment_json, env, origins[0].geometry)
        # TODO: this is not logical, just use a list
        tag = equipment_json['tags'][0]
        equipment[tag] = equipment_object

    activities = []
    for origin in origins:
        for destination in destinations:
            activity = model.Activity(
                env=env, name=origin.name + '_' + destination.name,
                origin=origin, destination=destination, **equipment
            )
            activities.append(activity)

    env.run()

    result = dict(
        completion_time=env.now,
        origins=get_logging(origins),
        destinations=get_logging(destinations),
        equipment=get_logging(list(equipment.values())),
        activities=get_logging(activities)
    )

    return jsonify(result)


def create_site(site_data, env):
    properties = site_data["properties"]
    kwargs = dict(
        env=env,
        name=properties["name"],
        geometry=shapely.geometry.asShape(site_data["geometry"]).centroid
    )

    tonnage = properties["capacity"] * ureg.metric_ton
    kwargs["capacity"] = tonnage.to_base_units().magnitude

    return Site(**kwargs)


def type_to_class_name(type):
    """convert lowercase types to python convention"""
    type_names = type.split()
    capitalized = [x.capitalize() for x in type_names]
    return ''.join(capitalized)


def compute_v_linear(v_empty, v_full):
    """return linear interpolation function for velocity"""
    return lambda x: x * (v_full - v_empty) + v_empty


def create_equipment(equipment, env, geometry):
    """factory function for equipment, uses global equipment data"""
    data = equipment
    mixin_classes = type_to_mixins_mapping[data["type"]]
    klass = type(
        type_to_class_name(data["type"]),
        mixin_classes,
        {}
    )

    kwargs = dict(env=env, name=data["name"])
    if issubclass(klass, core.Processor):
        processing_speed = (
            data['properties']['capacity'] * ureg.ton / ureg.minute
        ).to_base_units()
        kwargs['rate'] = processing_speed.magnitude
    if issubclass(klass, core.HasResource):
        kwargs['nr_resources'] = 1
    if issubclass(klass, core.HasContainer):
        tonnage = (data['properties']['tonnage'] * ureg.metric_ton).to_base_units()
        kwargs['capacity'] = tonnage.magnitude
    if issubclass(klass, core.HasFuel):
        # todo request something from data to calculate this
        kwargs['fuel_capacity'] = 1_000
    if issubclass(klass, core.Locatable):
        kwargs['geometry'] = geometry
    if issubclass(klass, core.Movable):
        speed_loaded = (data['properties']['speed loaded'] * ureg.knot).to_base_units().magnitude
        if issubclass(klass, core.ContainerDependentMovable):
            kwargs['compute_v'] = compute_v_linear(
                speed_loaded * 2, speed_loaded
            )
        else:
            kwargs['v'] = speed_loaded

    return klass(**kwargs)


def get_logging(object_list):
    """extract logging information"""
    logging = {}
    for mixin_object in object_list:
        logging[mixin_object.name] = mixin_object.get_log_as_json()
    return logging
