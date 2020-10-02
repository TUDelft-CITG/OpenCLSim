"""Component to locate the simulation objecs."""
import pyproj
import shapely.geometry


class Locatable:
    """
    Something with a geometry (geojson format).

    Parameters
    ----------
    lat : degrees
        can be a point as well as a polygon
    lon : degrees
    """

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry
        self.wgs84 = pyproj.Geod(ellps="WGS84")

    def is_at(self, locatable, tolerance=100):
        current_location = shapely.geometry.asShape(self.geometry)
        other_location = shapely.geometry.asShape(locatable.geometry)
        _, _, distance = self.wgs84.inv(
            current_location.x, current_location.y, other_location.x, other_location.y
        )

        return distance < tolerance
