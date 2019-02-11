import pytest
import simpy
import shapely.geometry
import logging
import numpy as np
import pint
import datetime
import time
import digital_twin.core as core
import digital_twin.model as model


def type_to_class_name(type):
    type_names = type.split()
    capitalized = [x.capitalize() for x in type_names]
    return ''.join(capitalized)

def compute_v_linear(v_empty, v_full):
    return lambda x: x * (v_full - v_empty) + v_empty

@pytest.fixture
def env():
    simulation_start = datetime.datetime(2019, 1, 1)
    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())
    return my_env

@pytest.fixture
def available_equipment(env):
    # should be read from database
    equipment_data = [
        {
            'id': 'EGG123',
            'type': 'Side stone dumping vessel',
            'speed loaded': 6.5,
            'tonnage': 2601,
            'lat': 52.94239823421129,
            'lon': 5.019298185633251,
            'tags': ['mover']
        },
        {
            'id': 'Boaty McBoatStone',
            'type': 'Multi purpose support vessel',
            'speed loaded': 7.0,
            'tonnage': 1824,
            'capacity': 10.3,
            'lat': 52.94239823421129,
            'lon': 5.019298185633251,
            'tags': ['loader', 'mover']
        },
        {
            'id': 'Loady McLoader',
            'type': 'Simple Loading Crane',
            'lat': 52.94239823421129,
            'lon': 5.019298185633251,
            'capacity': 13.2
        },
        {
            'id': 'Unloady McUnloader',
            'type': 'Simple Loading Crane',
            'lat': 52.94042293840172,
            'lon': 5.054676856441372,
            'capacity': 12.1
        }
    ]

    type_to_mixins_mapping = {
        'Side stone dumping vessel': (core.Identifiable, core.Log, core.ContainerDependentMovable, core.HasResource, core.Locatable),
        'Multi purpose support vessel': (core.Identifiable, core.Log, core.ContainerDependentMovable, core.Processor, core.HasResource, core.Locatable),
        'Simple Loading Crane': (core.Identifiable, core.Log, core.Processor, core.HasResource, core.Locatable)
    }

    ship_mixins = {}
    for data in equipment_data:
        ship_type = data['type']
        mixin_classes = type_to_mixins_mapping[ship_type]
        klass = type(type_to_class_name(ship_type), mixin_classes, {})
        ureg = pint.UnitRegistry()
        kwargs = dict(env=env, name=data['id'])
        if issubclass(klass, core.Processor):
            processing_speed = (data['capacity'] * ureg.ton / ureg.minute).to_base_units()
            kwargs['loading_func'] = (lambda x: x / processing_speed.magnitude)
            kwargs['unloading_func'] = (lambda x: x / processing_speed.magnitude)
        if issubclass(klass, core.HasResource):
            kwargs['nr_resources'] = 1
        if issubclass(klass, core.HasContainer):
            tonnage = (data['tonnage'] * ureg.metric_ton).to_base_units()
            kwargs['capacity'] = tonnage.magnitude
        if issubclass(klass, core.Locatable):
            # todo change this to something read from the database
            kwargs['geometry'] = shapely.geometry.Point(data['lon'], data['lat'])
        if issubclass(klass, core.Movable):
            speed_loaded = (data['speed loaded'] * ureg.knot).to_base_units().magnitude
            if issubclass(klass, core.ContainerDependentMovable):
                kwargs['compute_v'] = compute_v_linear(speed_loaded * 2, speed_loaded)
            else:
                kwargs['v'] = speed_loaded

        ship = klass(**kwargs)
        ship_mixins[data['id']] = ship
    return ship_mixins


# simple test to see if equipment list is generated correctly
def test_ship_list(available_equipment):
    print('')
    for id in available_equipment:
        print(id + ': ' + str(available_equipment[id]))

@pytest.fixture
def available_sites(env):
    # should be read from database
    # example of data expected for simple "point" sites
    site_data = [
        {
            'id': 'Den Oever',
            'lat': 52.94042293840172,
            'lon': 5.054676856441372,
            'tonnage': 20_000
        },
        {
            'id': 'Kornwerderzand',
            'lat': 53.06686424241725,
            'lon': 5.294877712236641,
            'tonnage': 30_000
        },
        {
            'id': 'Stockpile',
            'lat': 52.94239823421129,
            'lon': 5.019298185633251,
            'tonnage': 100_000
        }
    ]

    site_mixins = {}
    for data in site_data:
        klass = type('Site', (core.Identifiable, core.Log, core.Locatable, core.HasContainer, core.HasResource), {})
        kwargs = dict(env=env, name=data['id'], geometry=shapely.geometry.Point(data['lon'], data['lat']))

        ureg = pint.UnitRegistry()
        tonnage = (data['tonnage'] * ureg.metric_ton).to_base_units()
        kwargs['capacity'] = tonnage.magnitude

        site = klass(**kwargs)
        site_mixins[data['id']] = site
    return site_mixins


# simple test to see if site list is generated correctly
def test_site_list(available_sites):
    print('')
    for site in available_sites:
        print(site + ': ' + str(available_sites[site]))


def test_activity_fill_destination(env, available_equipment, available_sites):
    origin = available_sites['Stockpile']
    origin.container.put(origin.container.capacity)  # fill the origin container
    destination = available_sites['Den Oever']
    assert destination.container.capacity < origin.container.capacity

    kwargs = dict(env=env, name='MyFirstActivity',
                  origin=origin, destination=destination,
                  loader=available_equipment['Loady McLoader'], mover=available_equipment['EGG123'],
                  unloader=available_equipment['Unloady McUnloader'])
    model.Activity(**kwargs)

    assert origin.container.level == origin.container.capacity
    assert destination.container.level == 0

    env.run()
    print('Simulation completed in: ' + str(datetime.timedelta(seconds=env.now)))

    assert origin.container.level == origin.container.capacity - destination.container.capacity
    assert destination.container.level == destination.container.capacity


def test_activity_empty_origin(env, available_equipment, available_sites):
    origin = available_sites['Den Oever']
    origin.container.put(origin.container.capacity)  # fill the origin container
    destination = available_sites['Stockpile']
    assert origin.container.capacity < destination.container.capacity

    kwargs = dict(env=env, name='MyFirstActivity',
                  origin=origin, destination=destination,
                  loader=available_equipment['Unloady McUnloader'], mover=available_equipment['EGG123'],
                  unloader=available_equipment['Loady McLoader'])
    model.Activity(**kwargs)

    assert origin.container.level == origin.container.capacity
    assert destination.container.level == 0

    env.run()
    print('Simulation completed in: ' + str(datetime.timedelta(seconds=env.now)))

    assert origin.container.level == 0
    assert destination.container.level == origin.container.capacity


def test_activity_hopper(env, available_equipment, available_sites):
    origin = available_sites['Kornwerderzand']
    origin.container.put(origin.container.capacity)  # fill the origin container
    destination = available_sites['Den Oever']
    assert destination.container.capacity < origin.container.capacity

    hopper = available_equipment['Boaty McBoatStone']
    kwargs = dict(env = env, name='MyHopperActivity', origin=origin, destination=destination,
                  loader=hopper, mover=hopper, unloader=hopper)
    model.Activity(**kwargs)

    assert origin.container.level == origin.container.capacity
    assert destination.container.level == 0

    env.run()
    print('Simulation completed in: ' + str(datetime.timedelta(seconds=env.now)))

    assert origin.container.level == origin.container.capacity - destination.container.capacity
    assert destination.container.level == destination.container.capacity

