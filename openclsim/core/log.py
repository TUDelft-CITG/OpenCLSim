"""Component to log the simulation objecs."""
import datetime
import time
from enum import Enum

import shapely.geometry

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
            "Message": [],
            "Timestamp": [],
            "Value": [],
            "Geometry": [],
            "ActivityID": [],
            "ActivityState": [],
        }

    def log_entry(
        self, log, t, value, geometry_log, ActivityID, ActivityState=LogState.UNKNOWN
    ):
        self.log["Message"].append(log)
        self.log["Timestamp"].append(datetime.datetime.utcfromtimestamp(t))
        self.log["Value"].append(value)
        self.log["Geometry"].append(geometry_log)
        self.log["ActivityID"].append(ActivityID)
        self.log["ActivityState"].append(ActivityState.name)

    def get_log_as_json(self):
        json = []
        for msg, t, value, geometry_log, act_state in zip(
            self.log["Message"],
            self.log["Timestamp"],
            self.log["Value"],
            self.log["Geometry"],
            self.log["ActivityState"],
        ):
            json.append(
                dict(
                    type="Feature",
                    geometry=shapely.geometry.mapping(geometry_log)
                    if geometry_log is not None
                    else "None",
                    properties=dict(
                        message=msg,
                        time=time.mktime(t.timetuple()),
                        value=value,
                        state=act_state,
                    ),
                )
            )
        return json
