import simpy
import random
from datetime import timedelta
import math

# A Port class is defined to specify the port specifications (number of available berths, number of cranes, and water level)


class Port:
    def __init__(
        self,
        env,
        name,
        num_berths,
        num_cranes,
        water_level,
        annual_port_calls,
        annual_anchorage_visits,
        anchorage_delays,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # attributes related to port accessibility
        self.env = env
        self.name = name
        self.num_berths = num_berths
        self.num_cranes = num_cranes
        self.berths = simpy.Resource(env, capacity=num_berths)
        self.cranes = simpy.Resource(env, capacity=num_cranes)
        self.queues = []
        self.wait_times = []
        self.num_vessels = 4
        self.num_vessels_served = 1
        self.water_level = water_level
        self.accessibility = 0.3  # initial %x accessibility

        # attributes related to port processes
        self.annual_port_calls = annual_port_calls
        self.annual_anchorage_visits = annual_anchorage_visits
        self.anchorage_delays = anchorage_delays
        # self.vessel_types = ["container", "bulk", "dredger"]
        # self.turnaround_times = {vessel_type: [] for vessel_type in self.vessel_types}
        # self.berth_occupancies = {vessel_type: [] for vessel_type in self.vessel_types}
        # self.anchorage_occupancies = {
        #     vessel_type: [] for vessel_type in self.vessel_types
        # }

    def handle_vessel(self, vessel):
        # Check if water level is appropriate for navigating
        # accessibility is reduced by %10 if the water level is too low
        if self.water_level < 15:
            self.accessibility -= 0.1
            self.dredge()  # Select a dredging strategy

        arrival_time = self.env.now  # Record the time the ship arrives\
        with self.berths.request() as berth:
            with self.cranes.request() as crane:
                # Wait for available berth and crane
                yield berth
                yield crane

                unloading_start_time = self.env.now

                # Simulate the unloading process
                # Replace with actual unloading time distribution
                unloading_time = random.randint(1, 5)
                yield self.env.timeout(unloading_time)

                # Record the time the ship finishes unloading
                unloading_finish_time = self.env.now

                # Record the wait time for the ship in the queue
                wait_time = unloading_start_time - arrival_time
                self.wait_times.append(wait_time)

                # Record the number of ships served
                self.num_vessels_served += 1

                # Record the time the ship leaves the port
                departure_time = self.env.now

                # Record the total time the ship spent in the port
                total_time_in_port = departure_time - arrival_time

                # Record the ship's data
                self.queues.append(
                    (
                        arrival_time,
                        unloading_start_time,
                        unloading_finish_time,
                        departure_time,
                        total_time_in_port,
                    )
                )

    def generate_vessel(self):
        while True:
            # Generate ships at random intervals
            yield self.env.timeout(
                random.randint(1, 5)
            )  # Replace with actual interarrival time distribution

            # Create a new ship process
            self.num_vessels += 1
            self.env.process(self.handle_vessel(self.num_vessels))

    # def process_vessel(self, vessel):
    #     vessel_type = vessel.name.split("_")[0]
    #     if vessel_type not in self.vessel_types:
    #         raise ValueError(f"Invalid vessel type: {vessel_type}")

    #     port_calls = self.annual_port_calls[vessel_type] / 12
    #     anchorage_visits = self.annual_anchorage_visits[vessel_type] / 12
    #     anchorage_delays = self.anchorage_delays[vessel_type]
    #     berth_occupancy = (
    #         len(self.resources["Berth"]) / self.resources["Berth"].capacity
    #     )
    #     anchorage_occupancy = (
    #         len(self.resources["Anchorage"]) / self.resources["Anchorage"].capacity
    #     )
    #     turnaround_time = self.calculate_turnaround_time(
    #         port_calls,
    #         anchorage_visits,
    #         anchorage_delays,
    #         berth_occupancy,
    #         anchorage_occupancy,
    #     )
    #     self.turnaround_times[vessel_type].append(turnaround_time)
    #     self.berth_occupancies[vessel_type].append(berth_occupancy)
    #     self.anchorage_occupancies[vessel_type].append(anchorage_occupancy)
    #     yield self.env.timeout(timedelta(days=30))

    def run(self, sim_time):
        self.env.process(self.generate_vessel())
        self.env.run(until=sim_time)

        # Calculate key performance indicators
        avg_wait_time = sum(self.wait_times) / len(self.wait_times)
        avg_service_time = sum(data[4] for data in self.queues) / len(self.queues)
        avg_throughput = self.num_vessels_served / sim_time
        avg_turnaround_time = avg_wait_time + avg_service_time

        # Showing the port processes key performance indicators
        print("Average wait time: {:.2f}".format(avg_wait_time))
        print("Average service time: {:.2f}".format(avg_service_time))
        print("Average throughput: {:.2f}".format(avg_throughput))
        print("Accessibility: {:.2f}%".format(self.accessibility * 100))
        print("Turnaround time: {:.2f}".format(avg_turnaround_time))

    def dredge(self):
        # Select a dredging strategy based on current accessibility
        if self.accessibility <= 0.2:
            # Strategy 1: Rent a trailing suction hopper dredger to remove sediment and deepen the channel

            # (Reference: "Dredging: A Handbook for Engineers," 2nd Edition, by J. van den Herik and H. Voormolen, CRC Press, 2006)
            # Define parameters
            x = 400  # loading rate (tons per hour)
            f_p = 1000  # fuel price ($ per liter)
            f_co = 10  # fuel consumption rate (liters per hour)
            m_p = 200  # unit maintenance cost ($ per hour)
            c_p = 400  # unit crew cost ($ per hour)
            p = 20000  # engine power (kilowatts)
            d_l = 2000  # dredger length (meters)

            # defining different equations to calculate the dredger's cost
            dredger_speed = (p * 0.8) / (d_l * 0.5)
            dredging_speed = dredger_speed * (x / 60)
            dredging_time = (
                (1 - self.accessibility)
                * self.num_vessels
                * dredging_speed
                / dredger_speed
            )
            fuel_total_cost = (f_p * f_co) * dredging_time
            maintenance_total_cost = m_p * dredging_time
            crew_total_cost = c_p * dredging_time
            sediment_dredged = dredging_time * dredger_speed
            total_cost = fuel_total_cost + maintenance_total_cost + crew_total_cost

            self.accessibility = min(
                1, self.accessibility + dredging_speed / (dredger_speed * dredging_time)
            )
            print("* Trailing Suction Hopper Dredger selected.")
            print("Accessibility: {:.2f}%".format(self.accessibility * 100))
            print("dredger speed: {:.2f} miles per hour".format(dredger_speed))
            print("dredging speed: {:.2f} miles per hour".format(dredging_speed))
            print("dredgin time: {:.2f} hours".format(dredging_time))
            print("sediment dredged: {:.2f} cubic meters".format(sediment_dredged))
            print("total cost: {:.2f} USD".format(total_cost))

        if self.accessibility > 0.2 and self.accessibility <= 0.5:
            # Strategy 2: Rent a water injection dredger to remove sediment and deepen the channel

            # Define parameters
            total_volume = (
                1000000  # Total volume of material to be dredged (cubic meters)
            )
            dredger_volume = 50000
            dredging_rate = 5000  # Dredging rate of the water injection dredger (cubic meters per hour)
            operating_time = 100  # Operating time of the dredger (hours)
            hourly_rate = 10000  # Hourly rate of the dredger (USD per hour)
            fuel_consumption_rate = (
                200  # Fuel consumption rate of the dredger (liters per hour)
            )
            fuel_price = 1.5  # Price of fuel (USD per liter)
            emission_factor = (
                2.68  # Emission factor for diesel engines (kg CO2 per liter of fuel)
            )

            # Calculate dredging time
            dredging_time = total_volume / dredging_rate

            # Calculate fuel cost
            fuel_cost = fuel_consumption_rate * fuel_price * operating_time

            # Calculate equipment cost
            equipment_cost = hourly_rate * operating_time

            # Calculate total cost
            total_cost = fuel_cost + equipment_cost

            # Calculate fuel consumption
            fuel_consumption = fuel_consumption_rate * operating_time

            # Calculate emissions
            emissions = fuel_consumption * emission_factor
            self.accessibility = min(
                1, self.accessibility + (dredger_volume / total_volume)
            )

            # Print results
            print("* Water Injection Dredger is selected.")
            print(f"Dredging time: {dredging_time:.2f} hours")
            print("Accessibility: {:.2f}%.".format(self.accessibility * 100))
            print(f"Fuel cost: {fuel_cost:.2f} USD")
            print(f"Fuel consumption: {fuel_consumption:.2f} liters")
            print(f"Emissions: {emissions:.2f} kg CO2")
            print(f"Equipment cost: {equipment_cost:.2f} USD")
            print(f"Total cost: {total_cost:.2f} USD")

        if self.accessibility > 0.5 and self.accessibility <= 0.8:
            # Strategy 3: Deploy air bubble screen to reduce sediment accumulation

            # formulating the effectiveness of air bubble screen
            # Define parameters
            H = 5  # Depth of water (m)
            U = 1  # Velocity of flow (m/s)
            D = 0.01  # Diameter of bubbles (m)
            L = 50  # Length of air bubble screen (m)
            C0 = 200  # Initial sediment concentration (mg/L)
            C1 = 150  # Sediment concentration after using air bubble screen (mg/L)

            # Calculation of Reynolds number
            nu = 1.5 * 10**-6  # Kinematic viscosity of water (m^2/s)
            Re = U * D / nu

            # Calculation of settling velocity using Rouse equation
            Ws = (
                0.038 * math.sqrt(Re) * D * (H / (H + L)) ** (5 / 4)
            )  # Settling velocity (m/s)

            # Calculation of sediment transport rate
            Qt = 2 / 3 * math.pi * D**2 * Ws * C0

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
            total_capital_cost = (
                bubble_generator_cost * num_generators
                + air_compressor_cost * num_compressors
                + installation_cost
            )

            # Operating costs
            electricity_cost = 0.10  # cost per kWh
            electricity_consumption = 50  # kWh per day
            maintenance_cost = 0.02  # cost per dollar of equipment cost
            labor_cost = 20.0  # cost per hour of labor
            water_treatment_cost = 5000.0  # estimated cost per year
            total_operating_cost = (
                electricity_cost * electricity_consumption
                + maintenance_cost * total_capital_cost
                + labor_cost * num_operators
                + water_treatment_cost
            )

            # Environmental costs
            noise_barrier_cost = 20000.0  # estimated cost of noise barrier
            acoustic_monitoring_cost = 5000.0  # estimated cost of acoustic monitoring
            total_environmental_cost = noise_barrier_cost + acoustic_monitoring_cost

            # Insurance and liability costs
            liability_insurance_cost = 10000.0  # estimated cost of liability insurance
            total_insurance_cost = liability_insurance_cost

            # Opportunity costs
            lost_revenue_cost = (
                50000.0  # estimated cost of lost revenue during implementation
            )
            total_opportunity_cost = lost_revenue_cost

            # Total cost
            total_cost_air_bubble_screen = (
                total_capital_cost
                + total_operating_cost
                + total_environmental_cost
                + total_insurance_cost
                + total_opportunity_cost
            )

            self.accessibility = min(1, self.accessibility + Reduction_rate)
            print("* Air bubble screen is selected.")
            print("Accessibility: {:.2f}%.".format(self.accessibility * 100))
            print(
                "total cost of air bubble screen: {:.2f}".format(
                    total_cost_air_bubble_screen
                )
            )
            print("air bubble screen reduction rate: {:.2f}".format(Reduction_rate))

        else:
            # Strategy 3: Deploy current deflecting wall to reduce sediment intrusion

            # Define parameters
            water_depth = 10
            current_speed = 2
            sediment_concentration = 0.01
            wall_angle = math.radians(1200)  # angle of the current deflecting wall
            wall_length = 30  # length of the current deflecting wall in meters
            material_cost_per_square_meter = 100  # in USD

            # Calculate wall height based on wall angle
            wall_height = wall_length * math.sin(wall_angle)
            wall_area = wall_length * wall_height

            # Calculate sediment transport capacity
            sediment_transport_capacity = (
                0.033 * (sediment_concentration**1.5) * (water_depth**1.5)
            )

            # Calculate sediment transport rate
            sediment_transport_rate = current_speed * sediment_transport_capacity

            # Calculate sediment deposition rate behind the wall
            sediment_deposition_rate = (
                0.033
                * (sediment_concentration**1.5)
                * ((water_depth - wall_height) ** 1.5)
            )

            # Cost calculation based on wall material cost per square meter
            total_material_cost = wall_area * material_cost_per_square_meter

            # Calculate wall efficiency as the ratio of sediment deposition rate to sediment transport rate
            wall_efficiency = 0.9
            # wall_efficiency = sediment_deposition_rate / sediment_transport_rate

            # sediment_concentration_reduction = wall_efficiency * \
            #     (current_speed ** 2) * (sediment_concentration / (1.65 * (water_depth ** (1/6))))

            self.accessibility = min(1, self.accessibility + wall_efficiency)

            # Return wall efficiency
            print("* Current deflecting wall is selected.")
            print("Accessibility: {:.2f}%.".format(self.accessibility * 100))
            print(
                "total cost of current deflecting wall: {:.2f}".format(
                    total_material_cost
                )
            )
            # print(
            #     "current deflecting wall reduction rate: {:.2f}".format(
            #         sediment_concentration_reduction
            #     )
            # )
