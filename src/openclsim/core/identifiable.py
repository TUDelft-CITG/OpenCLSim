"""Component to identify the simulation objects."""

import uuid


class Identifiable:
    """
    OpenCLSim Identifiable with tags and a description.

    Parameters
    ----------
    name
        a human readable name to be used in logs and charts
    ID : UUID
        a unique id generated with uuid
    description
        Text that can be used to describe a simulation object.
        Note that this field does not influence the simulation.
    tags
        List of tags that can be used to identify objects.
        Note that this field does not influence the simulation.
    """

    def __init__(self, name: str, ID: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.id = ID if ID else str(uuid.uuid4())
