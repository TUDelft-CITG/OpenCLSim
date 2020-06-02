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
    "level": 6,
}  # The actual volume of the site
from_site = Site(**data_from_site)

basic_activity_data = {
    "env": my_env,
    "name": "Basic activity",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    "registry": registry,
    "duration": 14,
    "postpone_start": True,
}
activity = model.BasicActivity(**basic_activity_data)

while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "while",  # We are moving soil
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",  # For logging purposes
    "registry": registry,
    "sub_process": activity,
    # "condition_event": [from_site.container.get_empty_event, to_site.container.get_full_event],
    # "condition_event": from_site.container.get_full_event(),
    "condition_event": from_site.container.get_empty_event(),
    "postpone_start": False,
}
while_activity = model.WhileActivity(**while_data)


my_env.run()

log_df = pd.DataFrame(activity.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

while_df = pd.DataFrame(while_activity.log)
data_while = while_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

ee = from_site.container.get_empty_event(id_="default")
