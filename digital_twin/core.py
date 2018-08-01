# -*- coding: utf-8 -*-

"""Main module."""

# package(s) related to time, space and id
import uuid

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy

# spatial libraries
import shapely.geometry
import pyproj


class SimpyObject:
    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env


class Identifiable:
    """Something that has a name and id

    env: a simpy Environment
    name: a name
    id: a unique id generated with uuid"""

    def __init__(self, name, id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        # generate some id, in this case based on m
        self.id = id if id else str(uuid.uuid1())


class Location(SimpyObject):
    """Something with a geometry (geojson format)

    geometry: can be a point as well as a polygon"""

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry


class Container(SimpyObject):
    """Container class

    capacity: amount the container can hold
    level: amount the container holds
    container: a simpy object that can hold stuff
    total_requested: a counter needed to prevent over-handling"""

    def __init__(self, capacity, level=0, nr_resources=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.container = simpy.Container(self.env, capacity, init=level)
        self.total_requested = 0
        self.resource = simpy.Resource(self.env, capacity=nr_resources)


class Movable(SimpyObject):
    """Movable class

    v_empty: speed empty [m/s]
    v_full: speed full [m/s]
    resource: a simpy resource that can be requested"""

    def __init__(self,
                 v_empty, v_full,
                 nr_resources=1,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v_empty = v_empty
        self.v_full = v_full
        self.resource = simpy.Resource(self.env, capacity=nr_resources)
        self.wgs84 = pyproj.Geod(ellps='WGS84')

    def execute_move(self, origin, destination):
        """determine distance between origin and destination, and
        yield the time it takes to travel it"""
        orig = shapely.geometry.asShape(origin.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        forward, backward, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        #todo fix dependency between Movable and Container
        if self.container.level == self.container.capacity:
            yield self.env.timeout(distance / self.v_full)
            print('  distance full:  ' + '%4.2f' % (distance) + ' m')
            print('  sailing full:   ' + '%4.2f' % (self.v_full) + ' m/s')
            print('  duration:       ' + '%4.2f' % ((distance / self.v_full) / 3600) + ' hrs')

        elif self.container.level == 0:
            yield self.env.timeout(distance / self.v_empty)
            print('  distance empty: ' + '%4.2f' % (distance) + ' m')
            print('  sailing empty:  ' + '%4.2f' % (self.v_empty) + ' m/s')
            print('  duration:       ' + '%4.2f' % ((distance / self.v_empty) / 3600) + ' hrs')


class Process(SimpyObject):
    """Process class

    resource: a simpy resource that can be requested
    rate: rate with which quantity can be processed [amount/s]
    amount: amount to process"""

    def __init__(self,
                 rate, amount=0,
                 nr_resources=1,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=nr_resources)
        self.rate = rate
        self.amount = amount

    def execute_process(self, origin, destination, amount):
        """get amount from origin container, put amount in destination continater,
        and yield the time it takes to process it"""

        if type(origin).__name__ == "Site":
            with origin.resource.request() as my_get_turn:
                yield my_get_turn

                origin.container.get(amount)
                destination.container.put(amount)
                yield self.env.timeout(amount / self.rate)

                origin.log_entry('', self.env.now, origin.container.level)
                destination.log_entry('', self.env.now, destination.container.level)

                print('  process:        ' + '%4.2f' % ((amount / self.rate) / 3600) + ' hrs')

        elif type(destination).__name__ == "Site":
            with destination.resource.request() as my_put_turn:
                yield my_put_turn

                origin.container.get(amount)
                destination.container.put(amount)
                yield self.env.timeout(amount / self.rate)

                origin.log_entry('', self.env.now, origin.container.level)
                destination.log_entry('', self.env.now, destination.container.level)

                destination.resource.release(my_put_turn)

                print('  process:        ' + '%4.2f' % ((amount / self.rate) / 3600) + ' hrs')


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


class Site(Identifiable, Location, Log, Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TransportResource(Identifiable, Location, Log, Container, Movable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TransportProcessingResource(Identifiable, Location, Log, Container, Movable, Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ProcessingResource(Identifiable, Location, Log, Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
