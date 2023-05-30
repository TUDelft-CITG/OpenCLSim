import simpy
from .simpy_object import SimpyObject


class HasPriorityResource(SimpyObject):
    def __init__(self, env, num_resources):
        self.env = env
        self.resources = simpy.PriorityResource(env, capacity=num_resources)

    def process_vessel(self, name, priority, vessel_type):
        with self.resources.request(priority=priority) as req:
            yield req

            if vessel_type == "dredging":
                # Dredging vessels have priority
                print(
                    f"Dredging vessel {name} entered the berth at time {self.env.now}"
                )
                yield self.env.timeout(1)  # Simulate dredging operation
                print(
                    f"Dredging vessel {name} completed dredging at time {self.env.now}"
                )
            else:
                # Seagoing vessels have priority
                print(
                    f"Seagoing vessel {name} entered the berth at time {self.env.now}"
                )
                yield self.env.timeout(5)  # Simulate berthing and servicing time
                print(
                    f"Seagoing vessel {name} completed service at the berth at time {self.env.now}"
                )
