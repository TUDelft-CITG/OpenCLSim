"""Component to move the simulation objects."""
import logging
import warnings

import shapely.geometry

from .container import HasContainer, HasMultiContainer
from .locatable import Locatable
from .log import LogState
from .simpy_object import SimpyObject

logger = logging.getLogger(__name__)


class Routable(SimpyObject):
    """Mixin class: Something with a route (networkx node list format)

    - route: list of node-IDs
    -
    """

    def __init__(self, route, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.route = route


class Movable(SimpyObject, Locatable):
    """
    Movable class.

    Used for object that can move with a fixed speed
    geometry: point used to track its current location

    Parameters
    ----------
    v: speed
    """

    def __init__(self, v: float = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self._v = v

    def move(self, destination=None, engine_order=1.0, duration=None):
        """
        Determine distance between origin and destination.

        Yield the time it takes to travel based on speed properties and load factor of
        the speed.
        """
        if destination is None:
            raise ValueError("Movable in OpenCLSim does not support empty destination")

        # Log the start event
        self.log_entry(
            self.env.now,
            self.activity_id,
            LogState.START,
        )

        # Determine the sailing_duration
        if duration is not None:
            sailing_duration = duration
        else:
            sailing_duration = self.sailing_duration(
                self.geometry, destination, engine_order
            )

        # Check out the time based on duration of sailing event
        yield self.env.timeout(sailing_duration)

        # Set mover geometry to destination geometry
        self.geometry = shapely.geometry.shape(destination.geometry)

        # Log the stop event
        self.log_entry(
            self.env.now,
            self.activity_id,
            LogState.STOP,
        )

    @property
    def v(self):
        return self._v

    @property
    def currentspeed(self):
        warnings.warn(
            "The property `.currentspeed` is deprected. Use `.v` instead.",
            DeprecationWarning,
        )
        return self.v

    def sailing_duration(self, origin, destination, engine_order, verbose=True):
        """Determine the sailing duration."""
        orig = shapely.geometry.shape(self.geometry)
        dest = shapely.geometry.shape(destination.geometry)
        _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

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
    def currentspeed(self):
        warnings.warn(
            "The property `.currentspeed` is deprected. Use `.v` instead.",
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
    def currentspeed(self):
        warnings.warn(
            "The property `.currentspeed` is deprected. Use `.v` instead.",
            DeprecationWarning,
        )
        return self.v


class CanSailOnGraph(Routable, Movable):
    """Mixin class: Allows to move over nodes on a graph"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # call functions when passing edges
        self.on_pass_edge_functions = []
        assert hasattr(self.env, "FG"), "expected graph FG to be available on env"

    def pass_edge(self, origin: str, destination: str):
        """Pass an edge. The node pair origin destination should be available on the env.graph."""
        edge = self.env.graph.edges[origin, destination]
        # get origin and destination geometry
        origin_geometry = self.env.graph.nodes[origin]["geometry"]
        destination_geometry = self.env.graph.nodes[destination]["geometry"]
        edge_geometry = edge["geometry"]
        print("check if we need to reorder", edge_geometry, origin_geometry, destination_geometry)

        for on_pass_edge_function in self.on_pass_edge_functions:
            on_pass_edge_function(origin, destination)
