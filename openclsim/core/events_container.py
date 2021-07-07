"""EventsContainer provide a basic class for managing information which has to be stored in an object."""
import operator as py_opp

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
        super().__init__(env, capacity=store_capacity * 2)
        self._env = env
        self._container_events = {}

    def initialize_container(self, initials):
        """Initialize method used for MultiContainers."""

        for item in initials:
            assert "id" in item
            assert "capacity" in item
            assert "level" in item
            assert "_reservations" not in item["id"]

            container_item = {
                "id": item["id"],
                "capacity": item["capacity"],
                "level": item["level"],
            }
            reservation_item = {
                "id": f"{item['id']}_reservations",
                "capacity": item["capacity"],
                "level": item["level"],
            }

            super().put(container_item)
            super().put(reservation_item)

    @property
    def container_list(self):
        container_ids = []
        if len(self.items) > 0:
            container_ids = [
                item["id"] for item in self.items if "_reservations" not in item["id"]
            ]
        return container_ids

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

    def get_container_event(self, level, opp, id_="default"):
        assert opp in [
            "gt",
            "ge",
            "lt",
            "le",
        ], f"Chosen operator ({opp}) is not supported please choose from: 'gt', 'ge', 'lt', 'le'"

        self._container_events.setdefault((id_, level, opp), self._env.event())

        event = self._container_events.get((id_, level, opp))
        current_level = self.get_level(id_)
        event_status = getattr(py_opp, opp)(current_level, level)

        if not event or (not event_status and event.triggered):
            # If event_status is still correct keep it otherwise overwrite it.
            self._container_events[(id_, level, opp)] = self._env.event()

        self.update_container_events()
        return self._container_events[(id_, level, opp)]

    def get_empty_event(self, id_="default"):
        return self.get_container_event(0, "le", id_)

    def get_full_event(self, id_="default"):
        return self.get_container_event(self.get_capacity(id_), "ge", id_)

    def update_container_events(self):
        for (id_, level, opp), event in self._container_events.items():
            current_level = self.get_level(id_)
            event_status = getattr(py_opp, opp)(current_level, level)
            if event_status and not event.triggered:
                event.succeed()

    def put(self, amount, id_="default"):
        store_status = super().get(lambda state: state["id"] == id_).value
        store_status["level"] = store_status["level"] + amount
        put_event = super().put(store_status)
        put_event.callbacks.append(self._callback)

        yield put_event

    def get(self, amount, id_="default"):
        store_status = super().get(lambda state: state["id"] == id_).value
        store_status["level"] = store_status["level"] - amount
        get_event = super().put(store_status)
        get_event.callbacks.append(self._callback)

        yield get_event

    def _callback(self, event, id_="default"):
        self.update_container_events()
