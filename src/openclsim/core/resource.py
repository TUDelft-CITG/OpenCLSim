"""Component to add rescources to the simulation objects."""

import simpy

from .simpy_object import SimpyObject


class HasResource(SimpyObject):
    """
    HasProcessingLimit class.

    Adds a limited Simpy resource which should be requested before the object is
    used for processing: Processes request these resources to become a user
    (or to “own” them) and have to release them once they are done
    https://simpy.readthedocs.io/en/latest/topical_guides/resources.html#resources

    Parameters
    ----------
    nr_resources
        Number of rescources of the object (default 1)
    """

    def __init__(self, nr_resources: int = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=nr_resources)
