from .identifiable import Identifiable
from .resource import HasResource
from .simpy_object import SimpyObject


class HasPriorityResource(HasResource):
    def __init__(self, nr_resources=float("inf"), *arg, **kwarg):
        super().__init__(*arg, **kwarg)
        self.active_vessel = None
        self.nr_resources = nr_resources

    def request(self, priority=0, *arg, **kwarg):
        if self.active_vessel and priority > self.active_vessel.priority:
            self.active_vessel.interrupt()
        return super().request(priority=priority, *arg, **kwarg)

    def active_vessel(self, vessel):
        self.active_vessel = vessel


class PriorityVessel(HasResource, Identifiable):
    def __init__(self, name, env, priority, *arg, **kwarg):
        super().__init__(env, name, *arg, **kwarg)
        self.priority = priority

    def process_vessel(self, env, resource):
        with resource.request(priority=self.priority) as request:
            yield request
            print(
                f"{env.now:.1f}: Vessel {self.name} starts unloading at {self.destination}"
            )
            yield env.timeout(1)  # Unloading time
            print(
                f"{env.now:.1f}: Vessel {self.name} finishes unloading at {self.destination}"
            )


# def process_vessel(self, name, priority, vessel_type):
#     with self.resources.request(priority=priority) as req:
#         yield req

#         if vessel_type == "dredging":
#             # Dredging vessels have priority
#             print(
#                 f"Dredging vessel {name} entered the berth at time {self.env.now}"
#             )
#             yield self.env.timeout(1)  # Simulate dredging operation
#             print(
#                 f"Dredging vessel {name} completed dredging at time {self.env.now}"
#             )
#         else:
#             # Seagoing vessels have priority
#             print(
#                 f"Seagoing vessel {name} entered the berth at time {self.env.now}"
#             )
#             yield self.env.timeout(5)  # Simulate berthing and servicing time
#             print(
#                 f"Seagoing vessel {name} completed service at the berth at time {self.env.now}"
#             )
