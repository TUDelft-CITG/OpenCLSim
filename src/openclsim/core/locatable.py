"""Component to locate the simulation objects."""

from typing import Optional

import pyproj
import shapely.geometry
from shapely.geometry.base import BaseGeometry


class Locatable:
    """Something with a geometry (geojson format). Can be a point as well as a
    polygon. The object can also be located on a graph (with a node). That
    requires the extra and optional node attribute. Make sure to also update the
    geometry when sailing over graphs.

    Parameters
    ----------
    geometry : Shapely Geometry that determines the position of an object.
    Coordinates are expected to be in wgs84 lon, lat.
    node: Optional string that locates an object on a graph.

    """

    def __init__(
        self, geometry: BaseGeometry, node: Optional[str] = None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry
        # an optional node for locating an object on a network
        self.node = node
        # used for distance computation
        self.wgs84 = pyproj.Geod(ellps="WGS84")

    def is_at(self, locatable, tolerance=100):
        current_location = shapely.geometry.shape(self.geometry)
        other_location = shapely.geometry.shape(locatable.geometry)
        _, _, distance = self.wgs84.inv(
            current_location.x, current_location.y, other_location.x, other_location.y
        )

        return distance < tolerance

    def get_state(self):
        state = {}
        if hasattr(super(), "get_state"):
            state = super().get_state()

        state.update({"geometry": self.geometry})
        if self.node is not None:
            state["node"] = self.node

        return state
