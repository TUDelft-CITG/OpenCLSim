"""Component to log the simulation objects."""
import datetime
from enum import Enum

from .simpy_object import SimpyObject


class LogState(Enum):
    """
    LogState enumeration of all possible states of a Log object.

    Access the name using .name and the integer value using .value
    """

    START = 1
    STOP = 2
    WAIT_START = 3
    WAIT_STOP = 4
    UNKNOWN = -1


class Log(SimpyObject):
    """Log class to log the object activities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.log = {
            "Timestamp": [],
            "ActivityID": [],
            "ActivityState": [],
            "ObjectState": [],
            "ActivityLabel": [],
        }

    def log_entry(
        self,
        t,
        activity_id,
        activity_state=LogState.UNKNOWN,
        additional_state=None,
        activity_label={},
    ):
        object_state = self.get_state()
        if additional_state:
            object_state.update(additional_state)

        if activity_label != {}:
            assert activity_label.get("type") is not None
            assert activity_label.get("ref") is not None

        self.log["Timestamp"].append(datetime.datetime.utcfromtimestamp(t))
        self.log["ActivityID"].append(activity_id)
        self.log["ActivityState"].append(activity_state.name)
        self.log["ObjectState"].append(object_state)
        self.log["ActivityLabel"].append(activity_label)

    def get_state(self):
        """
        empty instance of the get state function.

        Add an empty instance of the get state function so that
        it is always available.
        """
        state = {}
        if hasattr(super(), "get_state"):
            state = super().get_state()
        return state
