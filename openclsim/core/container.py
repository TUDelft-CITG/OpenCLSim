"""Component that assigns a container to the simulation objecs."""
from .events_container import EventsContainer
from .simpy_object import SimpyObject


class HasContainer(SimpyObject):
    """
    A class which can hold information about objects of the same type.

    Parameters
    ----------
    capacity
        amount the container can hold
    level
        Amount the container holds initially
    store_capacity
        The number of different types of information can be stored. In this class it usually is 1.
    """

    def __init__(
        self,
        capacity: float,
        store_capacity: int = 1,
        level: float = 0.0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        # container_class = type(
        #    "CombinedContainer", (EventsContainer, ReservationContainer), {}
        # )
        container_class = EventsContainer
        self.container = container_class(self.env, store_capacity=store_capacity)
        if capacity > 0:
            self.container.initialize(capacity=capacity, init=level)
            # self.container.initialize_reservation(capacity=capacity, init=level)
