"""Component to move the simulation objects."""
import logging
from typing import List
import warnings


import shapely.geometry
import pyproj

from .container import HasContainer, HasMultiContainer
from .locatable import Locatable
from .log import LogState
from .simpy_object import SimpyObject

# can be removed if we switch to python>=3.10
try:
    from itertools import pairwise
except ImportError:
    def pairwise(iterable):
        # pairwise('ABCDEFG') --> AB BC CD DE EF FG
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)


logger = logging.getLogger(__name__)


class Movable(SimpyObject, Locatable):
    """
    Movable class.

    Used for object that can move with a fixed speed
    geometry: point used to track its current location

    Parameters
    ----------
    v: speed (1d)
    engine_order: factor that determines how much of the speed is used.
    """

    def __init__(self, v: float = 1, engine_order: float = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """"""
        self._v = v
        self.engine_order = 1

    def move(self, destination: Locatable = None, duration: float = None):
        """
        Determine distance between origin and destination.

        Yield the time it takes to travel based on speed properties and load factor of
        the speed.
        """
        if destination is None:
            raise ValueError("Movable in OpenCLSim does not support empty destination")

        # Log the start event
        self.log_entry_v1(
            self.env.now,
            self.activity_id,
            LogState.START,
        )

        # Determine the sailing_duration
        if duration is None:
            duration = self.duration(
                self.geometry, destination
            )

        # Check out the time based on duration of sailing event
        yield self.env.timeout(duration)

        # Set mover geometry to destination geometry
        print('updating to destination geometry', destination.geometry)
        self.geometry = shapely.geometry.shape(destination.geometry)

        # Log the stop event
        self.log_entry_v1(
            self.env.now,
            self.activity_id,
            LogState.STOP,
        )

    @property
    def v(self):
        """return the velocity * engine_order"""
        return self._v * self.engine_order

    @property
    def current_speed(self):
        warnings.warn(
            "The property `.current_speed` is deprected. Use `.v` instead.",
            DeprecationWarning,
        )
        return self.v

    @staticmethod
    def distance(origin, destination):
        """Determine the sailing distance based on great circle path from origin to destination."""
        orig = shapely.geometry.shape(self.geometry)
        dest = shapely.geometry.shape(destination.geometry)
        _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)
        return distance

    def duration(self, origin, destination, engine_order, verbose=True):
        """Determine the duration based on great circle path from origin to destination."""
        distance = self.distance(origin, destination)
        return distance / (self.v * engine_order)


class ContainerDependentMovable(Movable, HasContainer):
    """
    ContainerDependentMovable class.

    Used for objects that move with a speed dependent on the container level

    Parameters
    ----------
    compute_v
        a function that returns the current speed, given the fraction of the
        the container that is filled (in [0,1]), e.g.:
            lambda x: x * (v_full - v_empty) + v_empty
        It can also be constant, e.g.:
            lambda x: 10
    """

    def __init__(self, compute_v, *args, **kwargs):
        """Init of the containerdependent moveable."""
        super().__init__(*args, **kwargs)
        self.compute_v = compute_v

    @property
    def v(self):
        return self.compute_v(
            self.container.get_level() / self.container.get_capacity()
        )

    @property
    def current_speed(self):
        warnings.warn(
            "The property `.current_speed` is deprected. Use `.v` instead.",
            DeprecationWarning,
        )
        return self.v


class MultiContainerDependentMovable(Movable, HasMultiContainer):
    """
    MultiContainerDependentMovable class.

    Used for objects that move with a speed dependent on the container level.
    This movable is provided with a MultiContainer, thus can handle a container
    containing different objects.
    compute_v
        a function that returns the current speed, given the fraction of the
        the container that is filled (in [0,1]), e.g.:
            lambda x: x * (v_full - v_empty) + v_empty
        It can also be constant, e.g.:
            lambda x: 10
    """

    def __init__(self, compute_v, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_v = compute_v
        self.conainter_ids = self.container.container_list

    @property
    def v(self):
        sum_level = 0
        sum_capacity = 0
        for id_ in self.container.container_list:
            sum_level = self.container.get_level(id_)
            sum_capacity = self.container.get_capacity(id_)
        fill_degree = sum_level / sum_capacity
        return self.compute_v(fill_degree)

    @property
    def current_speed(self):
        warnings.warn(
            "The property `.current_speed` is deprected. Use `.v` instead.",
            DeprecationWarning,
        )
        return self.v

class Navigator:
    def find_route(waypoints):
        route = []
        return route

class Routable(SimpyObject):
    """Mixin class: Something with a route (networkx node list format)
    route: a list of node ids (available on env.graph) or geometries (shapely.Geometry)
    """

    def __init__(self, route: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # call functions when passing edges
        self.route = route
        self.on_pass_edge_functions = []
        self.wgs84 = pyproj.Geod(ellps="WGS84")
        assert hasattr(self.env, "FG"), "expected graph FG to be available on env"

    def move_to_geometry(self, geometry: shapely.geometry.Point):
        """move to geometry"""
        linestring = shapely.geometry.LineString([self.geometry, geometry])
        distance = self.wgs84.geometry_length(edge_geometry)
        duration = self.v * distance
        yield self.env.timeout(duration)
        self.geometry = geometry

    def pass_linestring(self, geometry):
        """Pass an edge. The node pair origin destination should be available on the env.graph."""
        assert isinstance(geometry, shapely.geometry.LineString)
        distance = self.wgs84.geometry_length(edge_geometry)
        duration = self.v * distance
        yield self.env.timeout(duration)
        self.geometry = destination_geometry


    @staticmethod
    def order_geometry(geometry: shapely.geometry.LineString, a: shapely.geometry.Point):
        """Make sure the linestring starts at a. If the end of the linestring is closer to a than the start, the linestring is inverted."""
        start = shapely.geometry.Point(*geometry.coords[0])
        end = shapely.geometry.Point(*geometry.coords[-1])
        _, _, distance_from_start = self.wgs84.inv(start.x, start.y, a.x, a.y)
        _, _, distance_from_end = self.wgs84.inv(end.x, end.y, a.x, a.y)
        if distance_from_start > distance_from_end:
            coords = np.flipud(np.array(geometry.coords))
        else:
            coords = geometry.coords
        new_geometry = shapely.geometry.LineString(coords)
        return new_geometry

    def move_over_route(self, route: List[str]):
        """sail over the route, a list of nodes"""
        a = route[0]
        a_geometry = self.graph.nodes[a]['geometry']
        yield from self.move_to_geometry(a_geometry)
        for i, (a, b) in enumerate(pairwise(route)):
            a_geometry = self.graph[a]['geometry']
            b_geometry = self.graph[b]['geometry']
            edge_geometry = self.graph[(a, b)]['geometry']
            # make sure we are in the right order
            edge_geometry = self.order_geometry(edge_geometry)
            yield from self.pass_linestring(edge_geometry)
            for pass_edge_function in self.pass_edge_function:
                yield pass_edge_function(ship=self, a=a, b=b, route=route, geometry=geometry)
