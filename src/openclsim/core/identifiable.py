"""Component to identify the simulation objects."""

import uuid
import warnings
from typing import Optional


class Identifiable:
    """
    OpenCLSim Identifiable with tags and a description.

    Parameters
    ----------
    name
        a human readable name to be used in logs and charts
    id : UUID
        a unique id generated with uuid
    description
        Text that can be used to describe a simulation object.
        Note that this field does not influence the simulation.
    tags
        List of tags that can be used to identify objects.
        Note that this field does not influence the simulation.
    """

    def __init__(self, name: str, id: Optional[str] = None, *args, **kwargs):
        # Deprecation
        if "ID" in kwargs:
            if id is not None:
                raise ValueError("Both ID and id are specified. Use id only.")

            warnings.warn(
                f"ID argument specified in {self}, please use the attribute id",
                category=DeprecationWarning,
                stacklevel=2,
            )
            id = kwargs.pop("ID")

        super().__init__(*args, **kwargs)
        self.name = name
        self.id = id if id else str(uuid.uuid4())
