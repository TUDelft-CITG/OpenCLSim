#!/usr/bin/env python
import json
import logging
import types

import simpy
import shapely.geometry
import pyproj

from digital_twin.core import SimpyObject
import digital_twin.model

logger = logging.getLogger(__name__)


def env(dct):
    if dct.get('__type__') == 'simpy.Environment':
        env = simpy.Environment()
        return env
    if dct.get('__type__') == 'simpy.Resource':
        resource = simpy.Resource(**dct)
        return resource
    if dct.get('__type__') == 'simpy.Container':
        container = simpy.Container(**dct)
        return resource
    if 'geometry' in dct:
        return shapely.geometry.asShape(dct)
    if dct.get('__type__') == 'pyproj.Geod':
        return pyproj.Geod(**dct)

    return dct

class EnvEnvoder(json.JSONEncoder):
    def default(self, obj):
        # not serialable, recognized  by key  in instance
        if isinstance(obj, simpy.Environment):
            return {'__type__': 'simpy.Environment'}
        elif getattr(obj, '__name__', None) == 'env':
            return {'__type__': 'simpy.Environment'}
        elif isinstance(obj, types.FunctionType):
            # we can't serialize functions
            logger.warn('could not serialize %s', obj)
            return None
        elif isinstance(obj, simpy.Resource):
            return {'capacity': obj.capacity}
        elif isinstance(obj, simpy.Container):
            return {'capacity': obj.capacity, 'level': obj.level}
        elif isinstance(obj, simpy.Process):
            logger.warn('could not serialize %s', obj)
            return None
        elif isinstance(obj, SimpyObject):
            dct = vars(obj)
            dct['__type__'] = obj.__class__.__name__
            return dct
        elif isinstance(obj, digital_twin.model.Condition):
            dct = vars(obj)
            dct['__type__'] = obj.__class__.__name__
            return dct
        elif isinstance(obj, types.FunctionType):
            # we can't serialize functions
            logger.warn('could not serialize %s', obj)
            return None

        elif hasattr(obj, '__geo_interface__'):
            # geospatial objects
            return obj.__geo_interface__
        elif isinstance(obj, pyproj.Geod):
            return {'initstring': obj.initstring, '__type__': 'pyproj.Geod'}

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def save(obj, path, **kwargs):
    result = obj.copy()

    with open(path, 'w') as f:
        json.dump(obj, f, cls=EnvEnvoder, **kwargs)


def load(path, **kwargs):
    """load json of model  configuration"""
    with open(path) as f:
        result = json.load(f, object_hook=env, **kwargs)
    return result
