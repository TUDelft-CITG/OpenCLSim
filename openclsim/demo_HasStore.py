# -*- coding: utf-8 -*-
"""
Created on Wed May  6 21:57:21 2020

@author: andre
"""
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
    "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # The coordinates of the project site
    "capacity": 10,  # The capacity of the site
    # "initial_objects": [{"id":1, "type":"MP", "destination":"Wind1"},
    #                  {"id":2, "type":"MP", "destination":"Wind2"},
    #                  {"id":3, "type":"MP", "destination":"Wind3"},
    #                  {"id":1, "type":"TP", "destination":"Wind1"},
    #                  {"id":2, "type":"TP", "destination":"Wind2"},
    #                  {"id":3, "type":"TP", "destination":"Wind3"}]
    "level": 5,
}  # The actual volume of the site

from_site = Site(**data_from_site)

#%%
[item["level"] for item in from_site.container.items if item["id"] == "default"][0]

from_site.container.items
from_site.container.peek()
from_site.container.get_level()
tt = from_site.container.put({"id": "default2", "level": 7, "capacity": 10})


def get_msg():
    msg = yield from_site.container.get()
    return msg


cont = from_site.container.get(3)
cont = from_site.container.get_raw()
cont.value
#%%
data_from_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "capacity": 10,  # The capacity of the site
    "initial_objects": [
        {"id": 1, "type": "MP", "destination": "Wind1"},
        {"id": 2, "type": "MP", "destination": "Wind2"},
        {"id": 3, "type": "MP", "destination": "Wind3"},
        {"id": 1, "type": "TP", "destination": "Wind1"},
        {"id": 2, "type": "TP", "destination": "Wind2"},
        {"id": 3, "type": "TP", "destination": "Wind3"},
    ],
}  # The actual volume of the site


def show_get(item):
    print(item.ok)


es = core.EventsStore(**data_from_site)
es.capacity
tt = es.get(lambda x: x["id"] == 1)
print(tt.value)
tt = es.get(lambda x: x["id"] == 1)
tt.processed
print(f"value: {tt.value}")
tt = es.get(lambda x: x["id"] == 1)
print(tt.value)


tt = es.get(lambda x: x["type"] == "MP")
print(tt.value)
#%%
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
data_hopper = {
    "env": my_env,  # The simpy environment
    "name": "Hopper 01",  # Name
    "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",  # For logging purposes
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 5,  # Capacity of the hopper - "Beunvolume"
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

move_activity_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Soil movement",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    "mover": hopper,
    "destination": to_site,
}

activity = model.MoveActivity(**move_activity_data)

my_env.run()

activity.log
log_df = pd.DataFrame(activity.log)
data = log_df[["Message", "Timestamp", "Value", "ActivityID"]]

