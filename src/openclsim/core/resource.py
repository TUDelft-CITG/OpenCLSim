"""Component to add rescources to the simulation objecs."""

import simpy

from .simpy_object import SimpyObject


class HasResource(SimpyObject):
    """
    HasProcessingLimit class.

    Adds a limited Simpy resource which should be requested before the object is
    used for processing.

    Parameters
    ----------
    nr_resources
        Number of rescources of the object
    """

    def __init__(self, nr_resources: int = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=nr_resources)
