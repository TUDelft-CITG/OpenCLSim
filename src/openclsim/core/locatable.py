"""Component to locate the simulation objects."""
import pyproj
import shapely.geometry


class Locatable:
    """
    Something with a geometry (geojson format).
    Can be a point as well as a polygon

    Parameters
    ----------
    lat : degrees (wgs84)
    lon : degrees (wgs84)
    """

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry
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
        return state
