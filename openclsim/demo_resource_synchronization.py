import datetime, time
import simpy

import shapely.geometry
from simplekml import Kml, Style

# package(s) for data handling
import pandas as pd
import numpy as np

import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot

simulation_start = 0

my_env = simpy.Environment(initial_time=simulation_start)
registry = {}

# The generic site class
Site = type(
    "Site",
    (
        core.Identifiable,  # Give it a name
        core.Log,  # Allow logging of all discrete events
        core.Locatable,  # Add coordinates to extract distance information and visualize
        core.HasContainer,  # Add information on the material available at the site
        core.HasResource,
    ),  # Add information on serving equipment
    {},
)  # The dictionary is empty because the site type is generic

# Information on the extraction site - the "from site" - the "win locatie"
location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat

data_from_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Winlocatie",  # The name of the site
    "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5d",  # For logging purposes
    "geometry": location_from_site,  # The coordinates of the project site
    "capacity": 10,  # The capacity of the site
    "level": 8,
}  # The actual volume of the site

# Information on the dumping site - the "to site" - the "dump locatie"
location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

data_to_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Dumplocatie",  # The name of the site
    "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5c",  # For logging purposes
    "geometry": location_to_site,  # The coordinates of the project site
    "capacity": 10,  # The capacity of the site
    "level": 0,
}  # The actual volume of the site (empty of course)

# The two objects used for the simulation
from_site = Site(**data_from_site)
to_site = Site(**data_to_site)


# The generic class for an object that can move and transport (a TSHD for example)
TransportProcessingResource = type(
    "TransportProcessingResource",
    (
        core.Identifiable,  # Give it a name
        core.Log,  # Allow logging of all discrete events
        core.ContainerDependentMovable,  # A moving container, so capacity and location
        core.Processor,  # Allow for loading and unloading
        core.HasResource,  # Add information on serving equipment
        core.HasCosts,  # Add information on costs
        core.LoadingFunction,  # Add a loading function
        core.UnloadingFunction,  # Add an unloading function
    ),
    {},
)

# For more realistic simulation you might want to have speed dependent on the volume carried by the vessel
def compute_v_provider(v_empty, v_full):
    return lambda x: 10


# TSHD variables
data_hopper1 = {
    "env": my_env,  # The simpy environment
    "name": "Hopper 01",  # Name
    "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 4,  # Capacity of the hopper - "Beunvolume"
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}

hopper1 = TransportProcessingResource(**data_hopper1)

data_hopper2 = {
    "env": my_env,  # The simpy environment
    "name": "Hopper 02",  # Name
    "ID": "5dbbbdf6-4589-11e9-95a2-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 4,  # Capacity of the hopper - "Beunvolume"
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
hopper2 = TransportProcessingResource(**data_hopper2)

requested_resources1 = {}
shift_amount_activity_loading_data1 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer1",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff52",  # For logging purposes
    "registry": registry,
    "processor": hopper1,
    "origin": from_site,
    "destination": hopper1,
    "amount": 1,
    "duration": 20,
    "postpone_start": True,
    #"keep_resources":[from_site],
    "requested_resources": requested_resources1,
}
activity1 = model.ShiftAmountActivity(**shift_amount_activity_loading_data1)

sequential_activity_data1 = {
    "env": my_env,
    "name": "Sequential process1",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
    "registry": registry,
    "sub_processes": [activity1],
    "postpone_start": True,
    "requested_resources": requested_resources1,
}
seq_activity1 = model.SequentialActivity(**sequential_activity_data1)

while_data1 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "while1",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
    "registry": registry,
    "sub_process": seq_activity1,
    "condition_event": [{"or":[{"type":"container", "concept": hopper1, "state":"full"},
               {"type":"container", "concept": from_site, "state":"empty"}]
         }],
    "postpone_start": False,
    "requested_resources": requested_resources1,
}
while_activity1 = model.WhileActivity(**while_data1)

shift_amount_activity_loading_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer2",  # We are moving soil
    "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff52",  # For logging purposes
    "registry": registry,
    "processor": hopper2,
    "origin": from_site,
    "destination": hopper2,
    "amount": 1,
    "duration": 20,
    "postpone_start": True,
}
activity2 = model.ShiftAmountActivity(**shift_amount_activity_loading_data2)

sequential_activity_data2 = {
    "env": my_env,
    "name": "Sequential process2",
    "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
    "registry": registry,
    "sub_processes": [activity2],
    "postpone_start": True,
}
seq_activity2 = model.SequentialActivity(**sequential_activity_data2)

expr = [{"type":"container", "concept": from_site, "state":"empty"}]
while_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "while2",  # We are moving soil
    "ID": "5dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
    "registry": registry,
    "sub_process": seq_activity2,
    "condition_event": [{"or":[{"type":"container", "concept": hopper2, "state":"full"},
               {"type":"container", "concept": from_site, "state":"empty"}]
         }],
    "postpone_start": False,
}
while_activity2 = model.WhileActivity(**while_data2)

my_env.run()

log_df = pd.DataFrame(from_site.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

log2_df = pd.DataFrame(activity1.log)
data2 = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

#%%
print(f"from_site: {from_site.container.get_level()}")
print(f"hopper1: {hopper1.container.get_level()}")
print(f"hopper2: {hopper2.container.get_level()}")