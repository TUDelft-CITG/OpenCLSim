"""Component to log the simulation objecs."""
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
    """
    Log class to log the object activities.

    log: log message [format: 'transfer activity' or 'move activity']
    t: timestamp
    value: a value can be logged as well
    geometry: value from locatable (lat, lon)
    ActivityState to explicate the meaning of the message
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.log = {
            "Timestamp": [],
            "ActivityID": [],
            "ActivityState": [],
            "ObjectState": [],
        }

    def log_entry(
        self,
        t,
        activity_id,
        activity_state=LogState.UNKNOWN,
        message=None,
    ):
        object_state = self.get_state()
        if message:
            object_state["message"] = message

        self.log["Timestamp"].append(datetime.datetime.utcfromtimestamp(t))
        self.log["ActivityID"].append(activity_id)
        self.log["ActivityState"].append(activity_state.name)
        self.log["ObjectState"].append(object_state)

    def get_state(self):
        """Add an empty instance of the get state function so that it is always available."""
        state = {}
        if hasattr(super(), "get_state"):
            state = super().get_state()
        return state
