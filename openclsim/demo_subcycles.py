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

# The generic site class
Site = type(
    "Site",
    (
        core.Identifiable,  # Give it a name
        core.Log,  # Allow logging of all discrete events
        core.Locatable,  # Add coordinates to extract distance information and visualize
        core.HasMultiContainer,  # Add information on the material available at the site
        core.HasResource,
    ),  # Add information on serving equipment
    {},
)  # The dictionary is empty because the site type is generic

# Information on the extraction site - the "from site" - the "win locatie"
location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat

data_from_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Winlocatie",  # The name of the site
    "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # The coordinates of the project site
    "store_capacity": 4,
    "initials": [
        {"id": "MP", "level": 5, "capacity": 10},
        {"id": "TP", "level": 5, "capacity": 10},
    ],
}  # The actual volume of the site

# Information on the dumping site - the "to site" - the "dump locatie"
location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

data_to_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Dumplocatie",  # The name of the site
    "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5b",  # For logging purposes
    "geometry": location_to_site,  # The coordinates of the project site
    "store_capacity": 4,
    "initials": [
        {"id": "MP", "level": 0, "capacity": 5},
        {"id": "TP", "level": 0, "capacity": 5},
    ],
}  # The actual volume of the site (empty of course)

# The two objects used for the simulation
from_site = Site(**data_from_site)
to_site = Site(**data_to_site)
# from_site.container.get_level()
# to_site.get_level()
cont = from_site.container

# The generic class for an object that can move and transport (a TSHD for example)
TransportProcessingResource = type(
    "TransportProcessingResource",
    (
        core.Identifiable,  # Give it a name
        core.Log,  # Allow logging of all discrete events
        core.MultiContainerDependentMovable,  # A moving container, so capacity and location
        core.Processor,  # Allow for loading and unloading
        core.HasResource,  # Add information on serving equipment
        core.HasCosts,  # Add information on costs
        core.LoadingFunction,  # Add a loading function
        core.UnloadingFunction,  # Add an unloading function
        # SiteRegistry,
    ),
    {"key": "MultiStoreHopper"},
)

# print(SiteRegistry.inspect("MultiStoreHopper"))
# For more realistic simulation you might want to have speed dependent on the volume carried by the vessel
def compute_v_provider(v_empty, v_full):
    return lambda x: 10


# TSHD variables
data_hopper = {
    "env": my_env,  # The simpy environment
    "name": "Hopper 01",  # Name
    "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "store_capacity": 4,
    "initials": [
        {"id": "MP", "level": 0, "capacity": 2},
        {"id": "TP", "level": 0, "capacity": 2},
    ],  # Capacity of the hopper - "Beunvolume"
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}


hopper = TransportProcessingResource(**data_hopper)
#%%

# activity = model.GenericActivity(
#     env=my_env,  # The simpy environment defined in the first cel
#     name="Soil movement",  # We are moving soil
#     ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
#     )
single_run = []

loading = []
shift_amount_loading_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff6a",  # For logging purposes
    "processor": hopper,
    "origin": from_site,
    "destination": hopper,
    "amount": 2,
    "duration": 10,
    "id_": "MP",
    "postpone_start": True,
}
loading.append(model.ShiftAmountActivity(**shift_amount_loading_data))

shift_amount_loading_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff6b",  # For logging purposes
    "processor": hopper,
    "origin": from_site,
    "destination": hopper,
    "amount": 2,
    "duration": 10,
    "id_": "TP",
    "postpone_start": True,
}
loading.append(model.ShiftAmountActivity(**shift_amount_loading_data2))

sequential_activity_data = {
    "env": my_env,
    "name": "loading",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
    "sub_processes": loading,
    "postpone_start": True,
}
single_run.append(model.SequentialActivity(**sequential_activity_data))

move_activity_to_site_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "sailing filler",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    "mover": hopper,
    "destination": to_site,
    "postpone_start": True,
}
single_run.append(model.MoveActivity(**move_activity_to_site_data))

unloading = []
shift_amount_unloading_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff7a",  # For logging purposes
    "processor": hopper,
    "origin": hopper,
    "destination": to_site,
    "amount": 2,
    "duration": 10,
    "id_": "MP",
    "postpone_start": True,
}
unloading.append(model.ShiftAmountActivity(**shift_amount_unloading_data))

shift_amount_unloading_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff7b",  # For logging purposes
    "processor": hopper,
    "origin": hopper,
    "destination": to_site,
    "amount": 2,
    "duration": 10,
    "id_": "TP",
    "postpone_start": True,
}
unloading.append(model.ShiftAmountActivity(**shift_amount_unloading_data2))

sequential_activity_data2 = {
    "env": my_env,
    "name": "unloading",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff80",  # For logging purposes
    "sub_processes": unloading,
    "postpone_start": True,
}
single_run.append(model.SequentialActivity(**sequential_activity_data2))


move_activity_to_harbor_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "sailing empty",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
    "mover": hopper,
    "destination": from_site,
    "postpone_start": True,
}
single_run.append(model.MoveActivity(**move_activity_to_harbor_data))

sequential_activity_data3 = {
    "env": my_env,
    "name": "Single run process",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff66",  # For logging purposes
    "sub_processes": single_run,
    "postpone_start": True,
}
activity = model.SequentialActivity(**sequential_activity_data3)

while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "while",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
    "sub_process": activity,
    # "condition_event": [from_site.container.get_empty_event, to_site.container.get_full_event],
    # "condition_event": my_env.all_of(events=[to_site.container.get_full_event(id_="MP"),to_site.container.get_full_event(id_="TP")]),
    "condition_event": to_site.container.get_full_event(id_="TP"),
    "postpone_start": False,
}
while_activity = model.WhileActivity(**while_data)

my_env.run()

log_df = pd.DataFrame(hopper.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data = data.drop_duplicates()

while_df = pd.DataFrame(while_activity.log)
data_while = while_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

#%%
print(
    f"hopper :{hopper.container.get_level(id_='MP')}MPs and {hopper.container.get_level(id_='TP')}TPs "
)
print(
    f"to_site :{to_site.container.get_level(id_='MP')}MPs and {to_site.container.get_level(id_='TP')}TPs "
)
print(
    f"hopper :{hopper.container.get_level(id_='MP')}MPs and {hopper.container.get_level(id_='TP')}TPs "
)
c = to_site.container
ee = c.get_full_event(id_="MP")
ee = c.full_event



