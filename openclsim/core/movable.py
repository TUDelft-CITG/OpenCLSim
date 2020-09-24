"""Component to move the simulation objecs."""
import logging

import shapely.geometry

from .container import HasContainer
from .locatable import Locatable
from .log import LogState
from .simpy_object import SimpyObject

logger = logging.getLogger(__name__)


class Movable(SimpyObject, Locatable):
    """
    Movable class.

    Used for object that can move with a fixed speed
    geometry: point used to track its current location

    Parameters
    ----------
    v
        speed
    """

    def __init__(self, v: float = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v = v

    def get_container_level(self):
        if hasattr(self, "container"):
            return self.container.get_level()
        else:
            return -1

    def move(self, destination, activity_name, engine_order=1.0, duration=None):
        """
        Determine distance between origin and destination.

        Yield the time it takes to travel based on flow properties and load factor of the flow.
        """

        origin_name = getattr(self, "name", "undefined")
        destination_name = getattr(destination, "name", "undefined")
        message = (
            f"move activity {activity_name} of {origin_name} to {destination_name}"
        )

        # Log the start event
        self.log_entry(
            message,
            self.env.now,
            self.get_container_level(),
            self.geometry,
            self.ActivityID,
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
        self.geometry = shapely.geometry.asShape(destination.geometry)

        # Debug logs
        logger.debug("  duration: " + "%4.2f" % (sailing_duration / 3600) + " hrs")

        # Log the stop event
        self.log_entry(
            message,
            self.env.now,
            self.get_container_level(),
            self.geometry,
            self.ActivityID,
            LogState.STOP,
        )

    @property
    def current_speed(self):
        return self.v

    def sailing_duration(self, origin, destination, engine_order, verbose=True):
        """Determine the sailing duration."""
        orig = shapely.geometry.asShape(self.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        return distance / (self.current_speed * engine_order)


class ContainerDependentMovable(Movable, HasContainer):
    """
    ContainerDependentMovable class.

    Used for objects that move with a speed dependent on the container level
    compute_v: a function, given the fraction the container is filled (in [0,1]), returns the current speed

    Parameters
    ----------
    v_empty
        Velocity of the vessel when empty
    v_full
        Velocity of the vessel when full
    """

    def __init__(self, v_empty: float = None, v_full: float = None, *args, **kwargs):
        """Init of the containerdependent moveable."""
        super().__init__(*args, **kwargs)
        v_full = v_full if v_full else 1
        v_empty = v_empty if v_empty else 1

        self.compute_v = lambda x: x * (v_full - v_empty) + v_empty

    @property
    def current_speed(self):
        return self.compute_v(
            self.container.get_level() / self.container.get_capacity()
        )
