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
        container_class = EventsContainer
        self.container = container_class(self.env, store_capacity=store_capacity)
        if capacity > 0:
            self.container.initialize(capacity=capacity, init=level)

    def get_state(self):
        state = {}
        if hasattr(super(), "get_state"):
            state = super().get_state()

        state.update({"container level": self.container.get_level()})
        return state


class HasMultiContainer(HasContainer):
    """
    A class which can represent information of objects of multiple types.

    store_capacity:  The number of different types of information can be stored. In this calss it is usually >1.
    initials: a list of dictionaries describing the id_ of the container, the level of the individual container and the capacity of the individual container.
    """

    def __init__(self, initials, store_capacity=10, *args, **kwargs):
        super().__init__(capacity=0, store_capacity=store_capacity, *args, **kwargs)
        self.container.initialize_container(initials)

    def get_state(self):
        state = {}
        if hasattr(super(), "get_state"):
            state = super().get_state()

        state.update(
            {
                "container level": {
                    container: self.container.get_level(id_=container)
                    for container in self.container.container_list
                }
            }
        )

        return state
