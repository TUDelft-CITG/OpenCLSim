import simpy
from .identifiable import Identifiable
from .simpy_object import SimpyObject


class ResourceAllocation(SimpyObject):
    def __init__(self, env, num_resources):
        self.env = env
        self.num_resources = num_resources
        self.resource_pool = simpy.PriorityResource(env, num_resources)
        self.location_claimed = False
        self.location_claimed_by = -1


class VesselClaim(Identifiable):
    def claim_location(self, name, priority):
        yield self.resource_pool.request(priority=priority)
        if not self.location_claimed:
            self.location_claimed = True
            self.location_claimed_by = name
            print(f"Vessel {name} claimed the location with priority {priority}")
        else:
            print(
                f"Vessel {name} failed to claim the location with priority {priority}"
            )
        yield self.env.timeout(1)  # time it takes to claim location

    def release_location(self, name):
        self.location_claimed = False
        self.location_claimed_by = -1
        self.resource_pool.release()
        print(f"Vessel {name} released the location")
