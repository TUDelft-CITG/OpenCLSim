import simpy
import random

# A Port class is defined to specify the port specifications (number of available berths, number of cranes, and water level)


class Port:
    def __init__(self, env, num_berths, num_cranes, water_level):
        self.env = env
        self.num_berths = num_berths
        self.num_cranes = num_cranes
        self.berths = simpy.Resource(env, capacity=num_berths)
        self.cranes = simpy.Resource(env, capacity=num_cranes)
        self.queues = []
        self.wait_times = []
        self.num_ships = 0
        self.num_ships_served = 0
        self.water_level = water_level
        self.accessibility = 0.5        # Starts at 100% accessibility

    def handle_ship(self, ship):

        # Check if water level is appropriate for navigating
        if self.water_level < 10:
            self.accessibility -= 0.1   # Reduce accessibility by 10% if water level is too low
            self.dredge()               # Select a dredging strategy

        # Record the time the ship arrives
        arrival_time = self.env.now

        with self.berths.request() as berth:
            # Wait for an available berth
            yield berth

            # Record the time the ship begins unloading
            unloading_start_time = self.env.now

            # Simulate the unloading process
            unloading_time = random.randint(1, 5)  # Replace with actual unloading time distribution
            yield self.env.timeout(unloading_time)

            # Record the time the ship finishes unloading
            unloading_finish_time = self.env.now

            # Record the wait time for the ship in the queue
            wait_time = unloading_start_time - arrival_time
            self.wait_times.append(wait_time)

            # Record the number of ships served
            self.num_ships_served += 1

        # Record the time the ship leaves the port
        departure_time = self.env.now

        # Record the total time the ship spent in the port
        total_time = departure_time - arrival_time

        # Record the ship's data
        self.queues.append((arrival_time, unloading_start_time, unloading_finish_time, departure_time, total_time))

    def generate_ship(self):
        while True:
            # Generate ships at random intervals
            yield self.env.timeout(random.randint(1, 5))  # Replace with actual interarrival time distribution

            # Create a new ship process
            self.num_ships += 1
            self.env.process(self.handle_ship(self.num_ships))

    def run(self, sim_time):
        self.env.process(self.generate_ship())
        self.env.run(until=sim_time)

        # Calculate key performance indicators
        avg_wait_time = sum(self.wait_times) / len(self.wait_times)
        avg_service_time = sum(data[4] for data in self.queues) / len(self.queues)
        avg_throughput = self.num_ships_served / sim_time

        print("Average wait time: {:.2f}".format(avg_wait_time))
        print("Average service time: {:.2f}".format(avg_service_time))
        print("Average throughput: {:.2f}".format(avg_throughput))
        print("Accessibility: {:.2f}%".format(self.accessibility * 100))

    def dredge(self):
        # Select a dredging strategy based on current accessibility
        if self.accessibility <= 0.5:
            # Strategy 1: Rent a dredger to remove sediment and deepen the channel
            dredger_cost = 5000  # Cost to rent a dredger for 1 day
            dredger_speed = 50  # Cubic meters of sediment dredged per hour
            dredging_speed = 10  # Cubic meters of sediment that accumulate per hour
            time_needed = (1 - self.accessibility) * self.num_ships * dredging_speed / dredger_speed
            sediment_dredged = time_needed * dredger_speed
            self.accessibility = min(1, self.accessibility + dredging_speed / (dredger_speed * time_needed))
            print("Dredging strategy 1 selected. Accessibility: {:.2f}%. Amount of sediment dredged: {:.2f} cubic meters.".format(
                self.accessibility * 100, sediment_dredged))
        else:
            # Strategy 2: Deploy underwater curtains to reduce sediment accumulation
            curtain_cost = 1000  # Cost to deploy curtains for 1 day
            curtain_effectiveness = 0.2  # Percentage reduction in sediment accumulation
            self.accessibility = min(1, self.accessibility + curtain_effectiveness)
            print("Dredging strategy 2 selected. Accessibility: {:.2f}%.".format(self.accessibility * 100))
