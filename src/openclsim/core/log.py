"""Component to log the simulation objects."""
import datetime
import numbers
import warnings
from enum import Enum
from numbers import Number
from typing import Any, Optional

import deprecated
import pandas as pd
import shapely

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
        # record oriented list of log messages
        self.logbook = []

    @property
    def log(self):
        """return the log in log format (compatible with old log attribute)"""
        df = pd.DataFrame(self.logbook)
        if not self.logbook:
            # add columns from old formats
            empty = {
                "Timestamp": [],
                "ActivityID": [],
                "ActivityState": [],
                "ObjectState": [],
                "ActivityLabel": [],
                "Message": [],
                "Value": [],
                "Geometry": [],
            }
            df = pd.DataFrame(empty)

        # Convert table to this format:
        # {'a': [1, 2], 'b': [2, 4]}
        list_format = df.to_dict(orient="list")

        return list_format

    # decorate the log setter.
    # throw a deprecation warning and ignore the setting
    @log.setter
    def log(self, value):
        """set the .log attribute (not allowed, will throw a deprecation warning)"""
        warnings.warn(
            ".log property is replaced by record format .logbook", DeprecationWarning
        )

    def log_entry_v1(
        self,
        t: Number,
        activity_id: Union[str, int],
        activity_state: LogState=LogState.UNKNOWN,
        additional_state: Optional[dict]=None,
        activity_label: Optional[dict]=None,
    ):
        """Log an entry (openclsim version).
        - Time (t) should b an timestamp in seconds since 1970 in utc.

        """

        object_state = self.get_state()
        if additional_state:
            object_state.update(additional_state)

        # default argument
        if activity_label is None or activity_label == {}:
            activity_label = {}
        else:
            # if an activity_label is passed
            assert activity_label.get("type") is not None
            assert activity_label.get("ref") is not None

        entry = {
            "Timestamp": datetime.datetime.utcfromtimestamp(t),
            "ActivityID": activity_id,
            "ActivityState": activity_state.name,
            "ObjectState": object_state,
            "ActivityLabel": activity_label,
        }
        self.logbook.append(entry)

    def log_entry_v0(self, log: str, t: numbers.Number, value, geometry_log: shapely.Geometry):
        """Log an entry (opentnsim version)"""
        assert isinstance(log, str), "expected log variable of type string"
        entry = {
            "Message": log,
            "Timestamp": datetime.datetime.fromtimestamp(t),
            "Value": value,
            "Geometry": geometry_log,
        }
        self.logbook.append(entry)

    @deprecated.deprecated(reason="Use .log_entry_v0 instead")
    def log_entry(self, *args, **kwargs):
        """Backward compatible log_entry. Calls the opentnsim variant."""
        assert (
            len(args) >= 2 or "t" in kwargs
        ), "Expected t as second argument or as named argument"
        if "t" in kwargs:
            t_argument = kwargs.get("t")
        else:
            t_argument = args[1]
        assert isinstance(
            t_argument, numbers.Number
        ), f"Expected t of type: Number, got {t_argument} of type: {type(t_argument)}"
        self.log_entry_v0(*args, **kwargs)

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
