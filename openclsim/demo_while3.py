# -*- coding: utf-8 -*-
"""
Created on Wed May  6 21:57:21 2020

@author: andre
"""
import datetime, time
import simpy

import shapely.geometry
from simplekml import Kml, Style


import pandas as pd
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
    "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5d",  # For logging purposes
    "geometry": location_from_site,  # The coordinates of the project site
    "store_capacity": 4,
    "initials": [
        {"id": "MP", "level": 2, "capacity": 10},
        {"id": "TP", "level": 0, "capacity": 2},
    ],  # Capacity of the hopper - "Beunvolume"
}  # The actual volume of the site
from_site = Site(**data_from_site)

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
    ),
    {},
)

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

shift_amount_activity_loading_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff52",  # For logging purposes
    "registry": registry,
    "processor": hopper,
    "origin": from_site,
    "destination": hopper,
    "amount": 1,
    "id_": "MP",
    "duration": 20,
    "postpone_start": True,
}
activity = model.ShiftAmountActivity(**shift_amount_activity_loading_data)


while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "while",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
    "registry": registry,
    "sub_process": activity,
    # "condition_event": [from_site.container.get_empty_event, to_site.container.get_full_event],
    # "condition_event": hopper.container.get_full_event(id_="MP"),
    "condition_event": from_site.container.get_empty_event(id_="MP"),
    "postpone_start": False,
}
while_activity = model.WhileActivity(**while_data)


my_env.run()

log_df = pd.DataFrame(hopper.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

while_df = pd.DataFrame(while_activity.log)
data_while = while_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]


#%%
print(f"hopper :{hopper.container.get_level('MP')}")
print(f"from_site :{from_site.container.get_level('MP')}")
# c = hopper.container
# ee = from_site.container.get_empty_event()
my_env.timeout(1)
ee = hopper.container.get_available(hopper.container.get_capacity(id_="MP"), id_="MP")
c = hopper.container
ee = c.put_available(c.get_capacity())
hopper.container.put_callback()
