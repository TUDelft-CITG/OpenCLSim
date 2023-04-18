class Priority:
    def __init__(self, priority, type):
        self._priority = {}

    def add_priority(self, type, priority):
        self._priority[type] = priority

    def get_priority(self, type):
        return self._priority[type]

    def vessel(self, type):
        if type == "dredging_vessel":
            priority = 1  # dredging vessel has priority to claim soil
            container = self.soil
        elif type == "seagoing_vessel":
            priority = 2  # seagoing vessel claims cargo container
            container = self.cargo
        else:
            raise ValueError("Invalid vessel type.")

        with container.request(priority=self.priority.get_priority(type)) as request:
            yield request
            print(f"{type} claimed the {container.type} container.")
            yield self.env.timeout(5 if type == "dredging_vessel" else 3)  # process container


class Location:
    def __init__(self, water_depth, channel_width, soil_quantity, cargo_quantity):
        self.water_depth = water_depth
        self.channel_width = channel_width
        self.soil_quantity = soil_quantity
        self.cargo_quantity = cargo_quantity
