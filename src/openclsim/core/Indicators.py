import simpy
import random
from datetime import timedelta
import math

# A Port class is defined to specify the port specifications (number of available berths, number of cranes, and water level)


class Port:
    def __init__(self, env, name, num_berths, num_cranes, water_level, annual_port_calls, annual_anchorage_visits, anchorage_delays, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # attributes related to port accessibility
        self.env = env
        self.num_berths = num_berths
        self.num_cranes = num_cranes
        self.berths = simpy.Resource(env, capacity=num_berths)
        self.cranes = simpy.Resource(env, capacity=num_cranes)
        self.queues = []
        self.wait_times = []
        self.num_ships = 3
        self.num_ships_served = 3
        self.water_level = water_level
        self.accessibility = 0.3       # Starts at x% accessibility

        # attributes related to port processes
        self.annual_port_calls = annual_port_calls
        self.annual_anchorage_visits = annual_anchorage_visits
        self.anchorage_delays = anchorage_delays
        self.vessel_types = ['container', 'bulk', 'dredger']
        self.turnaround_times = {vessel_type: [] for vessel_type in self.vessel_types}
        self.berth_occupancies = {vessel_type: [] for vessel_type in self.vessel_types}
        self.anchorage_occupancies = {vessel_type: [] for vessel_type in self.vessel_types}

    def handle_ship(self, ship):
        # Check if water level is appropriate for navigating
        if self.water_level < 15:
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

        # Showing the port processes key performance indicators
        print("Average wait time: {:.2f}".format(avg_wait_time))
        print("Average service time: {:.2f}".format(avg_service_time))
        print("Average throughput: {:.2f}".format(avg_throughput))
        print("Accessibility: {:.2f}%".format(self.accessibility * 100))

    def process_vessel(self, vessel):
        vessel_type = vessel.name.split('_')[0]
        if vessel_type not in self.vessel_types:
            raise ValueError(f'Invalid vessel type: {vessel_type}')
        port_calls = self.annual_port_calls[vessel_type] / 12
        anchorage_visits = self.annual_anchorage_visits[vessel_type] / 12
        anchorage_delays = self.anchorage_delays[vessel_type]
        berth_occupancy = len(self.resources['Berth']) / self.resources['Berth'].capacity
        anchorage_occupancy = len(self.resources['Anchorage']) / self.resources['Anchorage'].capacity
        turnaround_time = self.calculate_turnaround_time(
            port_calls, anchorage_visits, anchorage_delays, berth_occupancy, anchorage_occupancy
        )
        self.turnaround_times[vessel_type].append(turnaround_time)
        self.berth_occupancies[vessel_type].append(berth_occupancy)
        self.anchorage_occupancies[vessel_type].append(anchorage_occupancy)
        yield self.env.timeout(timedelta(days=30))

    def calculate_turnaround_time(self, port_calls, anchorage_visits, anchorage_delays, berth_occupancy, anchorage_occupancy):
        # calculate the expected time a vessel spends in the port based on the input parameters
        time_in_port = 2  # assume 2 days in port
        time_at_anchorage = 1  # assume 1 day at anchorage
        time_delayed_at_anchorage = time_at_anchorage * anchorage_delays
        time_in_transit = 4  # assume 4 days in transit
        total_time = (time_in_port + time_at_anchorage + time_delayed_at_anchorage + time_in_transit)
        return total_time / port_calls

    def dredge(self):
        # Select a dredging strategy based on current accessibility
        if self.accessibility <= 0.5:

            # Strategy 1: Rent a dredger to remove sediment and deepen the channel

            # (Reference: "Dredging: A Handbook for Engineers," 2nd Edition, by J. van den Herik and H. Voormolen, CRC Press, 2006)
            # assigning problem parameters
            x = 400   # loading rate (tons per hour)
            f_p = 1000   # fuel price ($ per liter)
            f_co = 10   # fuel consumption rate (liters per hour)
            m_p = 200   # unit maintenance cost ($ per hour)
            c_p = 400   # unit crew cost ($ per hour)
            p = 13000   # engine power (kilowatts)
            d_l = 2000  # dredger length (meters)

            # defining different equations to calculate the dredger's cost
            dredger_speed = (p * 0.8) / (d_l * 0.5)
            dredging_speed = dredger_speed * (x / 60)
            dredging_time = (1-self.accessibility) * self.num_ships * dredging_speed / dredger_speed
            fuel_total_cost = (f_p * f_co) * dredging_time
            maintenance_total_cost = m_p * dredging_time
            crew_total_cost = c_p * dredging_time
            sediment_dredged = dredging_time * dredger_speed
            total_cost = fuel_total_cost + maintenance_total_cost + crew_total_cost

            self.accessibility = min(1, self.accessibility + dredging_speed / (dredger_speed * dredging_time))
            print("Dredging strategy 1 selected. Accessibility: {:.2f}%. Amount of sediment dredged: {:.2f} cubic meters.".format(
                self.accessibility * 100, sediment_dredged))
            print("dredger speed: {:.2f}".format(dredger_speed))
            print("dredging speed: {:.2f}".format(dredging_speed))
            print("dredgin time: {:.2f}".format(dredging_time))
            print("sediment dredged: {:.2f}".format(sediment_dredged))
            print("total cost: {:.2f}".format(total_cost))
        else:

            # Strategy 2: Deploy air bubble screen to reduce sediment accumulation

            # formulating the effectiveness of air bubble screen
            # Input parameters
            H = 5   # Depth of water (m)
            U = 1   # Velocity of flow (m/s)
            D = 0.01    # Diameter of bubbles (m)
            L = 50   # Length of air bubble screen (m)
            C0 = 200    # Initial sediment concentration (mg/L)
            C1 = 150    # Sediment concentration after using air bubble screen (mg/L)

            # Calculation of Reynolds number
            nu = 1.5 * 10**-6  # Kinematic viscosity of water (m^2/s)
            Re = U * D / nu

            # Calculation of settling velocity using Rouse equation
            Ws = 0.038 * math.sqrt(Re) * D * (H/(H+L))**(5/4)   # Settling velocity (m/s)

            # Calculation of sediment transport rate
            Qt = 2/3 * math.pi * D**2 * Ws * C0

            # Calculation of sediment reduction percentage after using air bubble screen
            Reduction_rate = (C0 - C1) / C0

            # formulating the total cost of air bubble screen (Ozyurt et al. (2018)), (Wang et al. (2021))
            # Capital costs
            num_generators = 2
            num_compressors = 2
            num_operators = 4
            bubble_generator_cost = 1000  # cost per bubble generator
            air_compressor_cost = 5000  # cost per air compressor
            installation_cost = 10000  # estimated installation cost
            total_capital_cost = bubble_generator_cost * num_generators + air_compressor_cost * num_compressors + installation_cost

            # Operating costs
            electricity_cost = 0.10  # cost per kWh
            electricity_consumption = 50  # kWh per day
            maintenance_cost = 0.02  # cost per dollar of equipment cost
            labor_cost = 20.0  # cost per hour of labor
            water_treatment_cost = 5000.0  # estimated cost per year
            total_operating_cost = (electricity_cost * electricity_consumption + maintenance_cost *
                                    total_capital_cost + labor_cost * num_operators + water_treatment_cost)

            # Environmental costs
            noise_barrier_cost = 20000.0  # estimated cost of noise barrier
            acoustic_monitoring_cost = 5000.0  # estimated cost of acoustic monitoring
            total_environmental_cost = noise_barrier_cost + acoustic_monitoring_cost

            # Insurance and liability costs
            liability_insurance_cost = 10000.0  # estimated cost of liability insurance
            total_insurance_cost = liability_insurance_cost

            # Opportunity costs
            lost_revenue_cost = 50000.0  # estimated cost of lost revenue during implementation
            total_opportunity_cost = lost_revenue_cost

            # Total cost
            total_cost_air_bubble_screen = total_capital_cost + total_operating_cost + \
                total_environmental_cost + total_insurance_cost + total_opportunity_cost

            self.accessibility = min(1, self.accessibility + Reduction_rate)
            print("Dredging strategy 2 selected. Accessibility: {:.2f}%.".format(self.accessibility * 100))
            print("total cost of air bubble screen: {:.2f}".format(total_cost_air_bubble_screen))
            print("air bubble screen reduction rate: {:.2f}".format(Reduction_rate))
