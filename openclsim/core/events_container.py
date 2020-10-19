"""EventsContainer provide a basic class for managing information which has to be stored in an object."""
import simpy


class EventsContainer(simpy.FilterStore):
    """
    EventsContainer provide a basic class for managing information which has to be stored in an object.

    It is a generic container, which has a default behavior, but can be used for storing arbitrary objects.

    Parameters
    ----------
    store_capacity
        Number of stores that can be contained by the multicontainer
    """

    def __init__(self, env, store_capacity: int = 1, *args, **kwargs):
        super().__init__(env, capacity=store_capacity)
        self._env = env
        self._get_available_events = {}
        self._put_available_events = {}

    def initialize(self, init=0, capacity=0):
        """Initialize method is a convenience method for backwards compatibility reasons."""
        self.put(init, capacity)

    def initialize_container(self, initials):
        """Initialize method used for MultiContainers."""
        for item in initials:
            assert "id" in item
            assert "capacity" in item
            assert "level" in item
            super().put(item)

    def get_available(self, amount, id_="default"):
        if self.get_level(id_) >= amount:
            return self._env.event().succeed()
        if id_ in self._get_available_events:
            if amount in self._get_available_events[id_]:
                return self._get_available_events[id_][amount]
        # else case: id_ is not in self._get_available_events
        new_event = self._env.event()
        self._get_available_events[id_] = {}
        self._get_available_events[id_][amount] = new_event
        return new_event

    def get_capacity(self, id_="default"):
        if self.items is None:
            return 0
        res = [item["capacity"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def get_level(self, id_="default"):
        if self.items is None:
            return 0
        res = [item["level"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def put_available(self, amount, id_="default"):
        if self.get_capacity(id_) - self.get_level(id_) >= amount:
            return self._env.event().succeed()
        if id_ in self._put_available_events:
            if amount in self._put_available_events:
                return self._put_available_events[amount]
        new_event = self._env.event()
        self._put_available_events[id_] = {}
        self._put_available_events[id_][amount] = new_event
        return new_event

    def get_empty_event(self, start_event=False, id_="default"):
        if not start_event:
            return self.put_available(self.get_capacity(id_), id_)
        elif start_event.processed:
            return self.put_available(self.get_capacity(id_), id_)
        else:
            return self._env.event()

    def get_full_event(self, start_event=False, id_="default"):
        if not start_event:
            return self.get_available(self.get_capacity(id_), id_)
        elif start_event.processed:
            return self.get_available(self.get_capacity(id_), id_)
        else:
            return self._env.event()

    @property
    def empty_event(self):
        """Properties that are kept for backwards compatibility. mThey are NOT applicable for MultiContainers."""
        return self.put_available(self.get_capacity())

    @property
    def full_event(self):
        """Properties that are kept for backwards compatibility. mThey are NOT applicable for MultiContainers."""
        return self.get_available(self.get_capacity())

    def put(self, amount, capacity=0, id_="default"):
        current_amount = 0
        if len(self.items) > 0:
            status = super().get(lambda status: status["id"] == id_)
            # if status.ok:
            if status.triggered:
                status = status.value
                if "capacity" in status:
                    capacity = status["capacity"]
                if "level" in status:
                    current_amount = status["level"]
            else:
                raise Exception(
                    f"Failed to derive the previous version of container {id_}"
                )
        # this is a fall back in case the container is used with default
        put_event = super().put(
            {"id": id_, "level": current_amount + amount, "capacity": capacity}
        )
        put_event.callbacks.append(self.put_callback)
        return put_event

    def put_callback(self, event, id_="default"):
        if isinstance(event, simpy.resources.store.StorePut):
            if "id" in event.item:
                id_ = event.item["id"]
        if id_ in self._get_available_events:
            for amount in sorted(self._get_available_events[id_]):
                if self.get_level(id_) >= amount:
                    if id_ in self._get_available_events:
                        self._get_available_events[id_][amount].succeed()
                        del self._get_available_events[id_][amount]
                else:
                    return

    def get(self, amount, id_="default"):
        store_status = super().get(lambda state: state["id"] == id_).value
        store_status["level"] = store_status["level"] - amount
        get_event = super().put(store_status)
        get_event.callbacks.append(self.get_callback)
        return get_event

    def get_callback(self, event, id_="default"):
        # it is confusing that this is checking for storeput while doing a get
        # the reason is that subtracting from a container requires to get the complete
        # content of a container and then add the remaining content of the container
        # which creates a storeput
        if isinstance(event, simpy.resources.store.StorePut):
            if "id" in event.item:
                id_ = event.item["id"]
        if id_ in self._put_available_events:
            for amount in sorted(self._put_available_events[id_]):
                # if isinstance(self, ReservationContainer):
                #    if self.get_capacity(id_) - self.get_expected_level(id_) >= amount:
                #        self._put_available_events[amount].succeed()
                #        del self._put_available_events[amount]
                # el
                if self.get_capacity(id_) - self.get_level(id_) >= amount:
                    if id_ in self._put_available_events:
                        self._put_available_events[id_][amount].succeed()
                        del self._put_available_events[id_][amount]
                else:
                    return

    @property
    def container_list(self):
        container_ids = []
        if len(self.items) > 0:
            container_ids = [item["id"] for item in self.items]
        return container_ids
