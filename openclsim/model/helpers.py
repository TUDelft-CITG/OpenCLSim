"""Module with helper functions for the simulation."""
import logging

logger = logging.getLogger(__name__)


def get_subprocesses(item):
    """Get a list of all the activities an their subprocesses recursively."""
    items = [item]
    sub_items = getattr(item, "sub_processes", [])
    for i in sub_items:
        items.extend(get_subprocesses(i))
    return items


def register_processes(processes):
    """Register all the processes iteratively."""
    items = []
    for process in processes:
        items.extend(get_subprocesses(process))
    items = list(set(items))

    for item in items:
        item.main_process = None

    registerd_items = []
    for _ in range(100):
        unregistered_items = set(items) - set(registerd_items)
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
            "Due to  recursion in the events of the activities, not all the activities can be registered."
        )
