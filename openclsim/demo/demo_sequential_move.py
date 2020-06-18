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
keep_resources = []

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
    "level": 2,
}  # The actual volume of the site

# Information on the dumping site - the "to site" - the "dump locatie"
location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

data_to_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Dumplocatie",  # The name of the site
    "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5b",  # For logging purposes
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

reporting_activity_data = {
    "env": my_env,
    "name": "Reporting activity",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
    "registry": registry,
    "duration": 0,
    "postpone_start": False,
    "keep_resources": keep_resources,
}
reporting_activity = model.BasicActivity(**reporting_activity_data)

sub_processes = []
move_activity_data1 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Soil movement1",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    "registry": registry,
    "mover": hopper,
    "destination": to_site,
    "postpone_start": True,
    "keep_resources": keep_resources,
}
sub_processes.append(model.MoveActivity(**move_activity_data1))
basic_activity_data2 = {
    "env": my_env,
    "name": "Basic activity2",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
    "registry": registry,
    "duration": 5,
    # "additional_logs": [hopper],
    "postpone_start": True,
    "keep_resources": keep_resources,
}
sub_processes.append(model.BasicActivity(**basic_activity_data2))
move_activity_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Soil movement2",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
    "registry": registry,
    "mover": hopper,
    "destination": from_site,
    "postpone_start": True,
    "keep_resources": keep_resources,
}
sub_processes.append(model.MoveActivity(**move_activity_data2))

sequential_activity_data = {
    "env": my_env,
    "name": "Sequential process",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
    "registry": registry,
    "sub_processes": (proc for proc in sub_processes),
    "keep_resources": keep_resources,
}
activity = model.SequentialActivity(**sequential_activity_data)

my_env.run()

log_df = pd.DataFrame(activity.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

hopper_log_df = pd.DataFrame(hopper.log)
data_hop = hopper_log_df[
    ["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]
]
data_hop = data_hop.drop_duplicates()

basic = []
for proc in sub_processes:
    df = pd.DataFrame(proc.log)
    basic.append(df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]])

rep_log_df = pd.DataFrame(reporting_activity.log)
data_rep = rep_log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data_rep = data_rep.drop_duplicates()
