# -*- coding: utf-8 -*-

"""Main module."""

# package(s) related to time, space and id
import uuid
import logging
import json

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy

# spatial libraries
import shapely.geometry
import pyproj

logger = logging.getLogger(__name__)


class SimpyObject:
    """General object which can be extended by any class requiring a simpy environment

    env: a simpy Environment
    """
    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env


class Identifiable:
    """Something that has a name and id

    name: a name
    id: a unique id generated with uuid"""

    def __init__(self, name, id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        # generate some id, in this case based on m
        self.id = id if id else str(uuid.uuid1())


class Locatable:
    """Something with a geometry (geojson format)

    geometry: can be a point as well as a polygon"""

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry


class HasContainer(SimpyObject):
    """Container class

    capacity: amount the container can hold
    level: amount the container holds initially
    container: a simpy object that can hold stuff"""

    def __init__(self, capacity, level=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.container = simpy.Container(self.env, capacity, init=level)


class Movable(SimpyObject, Locatable):
    """Movable class todo doc"""

    def __init__(self, v=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v = v
        self.wgs84 = pyproj.Geod(ellps='WGS84')

    def move(self, destination):
        """determine distance between origin and destination, and
        yield the time it takes to travel it"""
        orig = shapely.geometry.asShape(self.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        forward, backward, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        speed = self.current_speed
        yield self.env.timeout(distance / speed)
        self.geometry = dest
        logger.debug('  distance: ' + '%4.2f' % distance + ' m')
        logger.debug('  sailing:  ' + '%4.2f' % speed + ' m/s')
        logger.debug('  duration: ' + '%4.2f' % ((distance / speed) / 3600) + ' hrs')

    @property
    def current_speed(self):
        return self.v


class ContainerDependentMovable(Movable, HasContainer):
    """Movable class

    v_empty: speed empty [m/s]
    v_full: speed full [m/s]
    resource: a simpy resource that can be requested"""

    def __init__(self,
                 compute_v,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_v = compute_v
        self.wgs84 = pyproj.Geod(ellps='WGS84')

    @property
    def current_speed(self):
        return self.compute_v(self.container.level / self.container.capacity)


class HasProcessingLimit(SimpyObject):
    """HasProcessingLimit class

    Adds a limited Simpy resource which should be requested before the object is used for processing."""

    def __init__(self, limit=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=limit)


class Log(SimpyObject):
    """Log class

    log: log message [format: 'start activity' or 'stop activity']
    t: timestamp
    value: a value can be logged as well"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.log = []
        self.t = []
        self.value = []

    def log_entry(self, log, t, value):
        """Log"""
        self.log.append(log)
        self.t.append(t)
        self.value.append(value)


class Processor(SimpyObject):
    """Processor class

    rate: rate with which quantity can be processed [amount/s]"""

    def __init__(self, rate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.rate = rate

    # noinspection PyUnresolvedReferences
    def process(self, origin, destination, amount):
        """get amount from origin container, put amount in destination container,
        and yield the time it takes to process it"""
        assert isinstance(origin, HasProcessingLimit) or isinstance(destination, HasProcessingLimit)
        assert origin.container.level >= amount
        assert destination.container.capacity - destination.container.level >= amount

        if isinstance(origin, HasProcessingLimit):
            with origin.resource.request() as my_get_turn:
                yield my_get_turn

                origin.container.get(amount)
                destination.container.put(amount)
                yield self.env.timeout(amount / self.rate)

                origin.log_entry('', self.env.now, origin.container.level)
                destination.log_entry('', self.env.now, destination.container.level)

                logger.debug('  process:        ' + '%4.2f' % ((amount / self.rate) / 3600) + ' hrs')

        elif isinstance(destination, HasProcessingLimit):
            with destination.resource.request() as my_put_turn:
                yield my_put_turn

                origin.container.get(amount)
                destination.container.put(amount)
                yield self.env.timeout(amount / self.rate)

                origin.log_entry('', self.env.now, origin.container.level)
                destination.log_entry('', self.env.now, destination.container.level)

                logger.debug('  process:        ' + '%4.2f' % ((amount / self.rate) / 3600) + ' hrs')


class Site(Identifiable, Locatable, Log, HasContainer, HasProcessingLimit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TransportResource(Identifiable, Log, HasContainer, Movable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TransportProcessingResource(Identifiable, Log, HasContainer, Movable, Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ProcessingResource(Identifiable, Locatable, Log, Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DictEncoder(json.JSONEncoder):
    """serialize a simpy digital_twin object to json"""
    def default(self, o):
        result = {}
        for key, val in o.__dict__.items():
            if isinstance(val, simpy.Environment):
                continue
            if isinstance(val, simpy.Container):
                result['capacity'] = val.capacity
                result['level'] = val.level
            else:
                result[key] = val

        return result


def serialize(obj):
    return json.dumps(obj, cls=DictEncoder)
