"""Component to log the simulation objects."""

import datetime
import numbers
import warnings
from enum import Enum
from typing import Optional, Union

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


class PerformsActivity:
    """An object can perform activities. For example a ship might be moing as
    part of a project activity like mobilization ("mobilization"). In that case
    you want to keep track of the activity that resulted in the move step. To
    keep track of this moving activity we keep track of more project based
    perspective on events we use the [Process
    Mining](https://processmining.org/event-data.html) concepts.

    From a process mining perspective:
    A ship might have an assignment to move soil from A to B.
    The ship (self) is than the a identifiable (.id) resource.
    The business transaction that resulted in the moving of the good would be a case id (not implemented)
    The activity_id is an identifier that stores which activity took place (for example "mobilization" or "shift A-B")
    Time is recorded in log events.
    """

    def __init__(self, activity_id: Union[int, str, None] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.activity_id = activity_id


class Log(SimpyObject):
    """Log class to log the object activities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        # record oriented list of log messages
        self.logbook = []

    @property
    def log(self):
        """
        Return the log in log format (compatible with old log attribute).

        The log can contain the following columns:
            Timestamp: datetime
            ActivityID: str
            ActivityState: dict
            ObjectState: dict
            ActivityLabel: dict
        """

        df = pd.DataFrame(self.logbook)

        columns = [
            "Timestamp",
            "ActivityID",
            "ActivityState",
            "ObjectState",
            "ActivityLabel",
        ]
        # only return columns that we know from openclsim
        columns_to_drop = set(df.columns) - set(columns)

        df = df.drop(columns=columns_to_drop)

        df = df.dropna(how="all")

        if not self.logbook:
            # add columns from old formats
            empty = {
                "Timestamp": [],
                "ActivityID": [],
                "ActivityState": [],
                "ObjectState": [],
                "ActivityLabel": [],
            }
            dtypes = {
                "Timestamp": "datetime64[ns]",
                "ActivityID": object,
                "ActivityState": object,
                "ObjectState": object,
                "ActivityLabel": object,
            }
            df = pd.DataFrame(empty)
            # cast to types
            for key, val in dtypes.items():
                df[key] = df[key].astype(val)

        # ensure we keep python datetimes and not timestamps. Timestamps will be cast to ints at the next step
        # no way to do this without a loop or warnings at the moment
        datetimes = pd.Series(
            [x.to_pydatetime() for x in df["Timestamp"].tolist()], dtype=object
        )

        df["Timestamp"] = datetimes

        # Convert table to this format:
        # {'a': [1, 2], 'b': [2, 4]}
        #
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
        t: float,
        activity_id: Union[str, int, None] = None,
        activity_state: LogState = LogState.UNKNOWN,
        additional_state: Optional[dict] = None,
        activity_label: Optional[dict] = None,
    ):
        """
        Log an entry (openclsim version).

        Parameters
        ----------
        t : float
            Timestamp in seconds since 1970 in utc.
        activity_id : Union[str, int, None], optional
            Identifier of the activity, by default None
        activity_state : LogState, optional
            State of the activity, by default LogState.UNKNOWN
        additional_state : Optional[dict], optional
            Additional state of the activity, by default None
        activity_label : Optional[dict], optional
            Label of the activity, by default None

        """

        object_state = self.get_state()
        if additional_state:
            object_state.update(additional_state)

        # default argument
        if activity_label is None:
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

    def log_entry_v0(self, log: str, t: float, value, geometry_log: shapely.Geometry):
        """Log an entry (opentnsim version)"""
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
