"""Module with helper functions for the simulation."""

import logging

logger = logging.getLogger(__name__)


def get_subprocesses(items):
    """Get a list of all the activities an their subprocesses recursively."""
    if not isinstance(items, list):
        items = [items]
    else:
        # This creates a new list with the same items.
        items = [i for i in items]

    for item in items:
        items.extend(getattr(item, "sub_processes", []))
    return items


def register_processes(processes):
    """Register all the (sub)processes iteratively."""
    items = get_subprocesses(processes)

    item_names = [i.name for i in items]
    assert len(item_names) == len(set(item_names))

    for item in items:
        item.main_process = None

    registerd_items = []
    for _ in range(100):
        # Subtracting sets does not work since this changes the order, which will
        # introduce randomness in the output.
        unregistered_items = [
            i for i in items if i.name not in [e.name for e in registerd_items]
        ]
        if len(unregistered_items) == 0:
            break
        for item in unregistered_items:
            try:
                item.register_process()
                registerd_items.append(item)
            except Exception as e:
                logger.info(e)
    else:
        raise ValueError(
            "Due to recursion in the events of the activities, not all the activities "
            "can be registered."
        )
