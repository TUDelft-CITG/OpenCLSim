import pytest
import simpy
import shapely.geometry
import logging
import numpy as np
import pint
import digital_twin.core as core


def type_to_class_name(type):
    type_names = type.split()
    capitalized = [x.capitalize() for x in type_names]
    return ''.join(capitalized)

def compute_v_linear(v_empty, v_full):
    return lambda x: x * (v_full - v_empty) + v_empty

@pytest.fixture
def env():
    return simpy.Environment()

@pytest.fixture
def generate_equipment_list(env):
    # should be read from database
    equipment_data = [
        {
            'id': 'EGG123',
            'type': 'Side stone dumping vessel',
            'speed loaded': 6.5,
            'tonnage': 2601,
            'tags': ['mover']
        },
        {
            'id': 'Boaty McBoatStone',
            'type': 'Multi purpose support vessel',
            'speed loaded': 7.0,
            'tonnage': 1824,
            'capacity': 10.3,
            'tags': ['loader', 'mover']
        },{
            'id': 'Loady McLoader',
            'type': 'Simple Loading Crane',
            'capacity': 13.2
        }
    ]

    type_to_mixins_mapping = {
        'Side stone dumping vessel': (core.Identifiable, core.Log, core.ContainerDependentMovable, core.HasResource),
        'Multi purpose support vessel': (core.Identifiable, core.Log, core.ContainerDependentMovable, core.Processor, core.HasResource),
        'Simple Loading Crane': (core.Identifiable, core.Log, core.Processor, core.HasResource)
    }

    ship_mixins = []
    for data in equipment_data:
        ship_type = data['type']
        mixin_classes = type_to_mixins_mapping[ship_type]
        klass = type(type_to_class_name(ship_type), mixin_classes, {})
        ureg = pint.UnitRegistry()
        kwargs = dict(env=env, name=data['id'])
        if issubclass(klass, core.Processor):
            processing_speed = (data['capacity'] * ureg.ton / ureg.minute).to_base_units()
            kwargs['rate'] = processing_speed
        if issubclass(klass, core.HasResource):
            kwargs['nr_resources'] = 1
        if issubclass(klass, core.HasContainer):
            tonnage = (data['tonnage'] * ureg.metric_ton).to_base_units()
            kwargs['capacity'] = tonnage.magnitude
        if issubclass(klass, core.Locatable):
            # todo change this to something read from the database
            kwargs['geometry'] = shapely.geometry.Point(4.066045, 51.985577)
        if issubclass(klass, core.Movable):
            speed_loaded = (data['speed loaded'] * ureg.knot).to_base_units()
            if issubclass(klass, core.ContainerDependentMovable):
                kwargs['compute_v'] = compute_v_linear(speed_loaded * 2, speed_loaded)
            else:
                kwargs['v'] = speed_loaded

        ship = klass(**kwargs)
        ship_mixins.append(ship)
    return ship_mixins


# simple test to see if equipment list is generated correctly
def test_ship_list(generate_equipment_list):
    print(generate_equipment_list[0])
    print(generate_equipment_list[1])
    print(generate_equipment_list[2])
