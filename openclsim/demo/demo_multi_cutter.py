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
    "name": "Winlocatie1",  # The name of the site
    "geometry": location_from_site,  # The coordinates of the project site
    "capacity": 4,
    "level": 4,
    "nr_resources":3,
    }  # The actual volume of the site
from_site = Site(**data_from_site)

location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

data_to_site = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Dumplocatie",  # The name of the site
    "geometry": location_to_site,  # The coordinates of the project site
    "capacity": 12,
    "level": 0,
}  # The actual volume of the site (empty of course)
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
        # SiteRegistry,
    ),
    {"key": "MultiStoreHopper"},
)

# print(SiteRegistry.inspect("MultiStoreHopper"))
# For more realistic simulation you might want to have speed dependent on the volume carried by the vessel
def compute_v_provider(v_empty, v_full):
    return lambda x: 10

data_cutter1 = {
    "env": my_env,  # The simpy environment
    "name": "Cutter1",  # Name
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 1,
    "level": 0,
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
cutter1 = TransportProcessingResource(**data_cutter1)
data_cutter2 = {
    "env": my_env,  # The simpy environment
    "name": "Cutter2",  # Name
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 1,
    "level": 0,
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
cutter2 = TransportProcessingResource(**data_cutter2)

# TSHD variables
data_hopper1 = {
    "env": my_env,  # The simpy environment
    "name": "Hopper1",  # Name
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 1,
    "level": 0,
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
hopper1 = TransportProcessingResource(**data_hopper1)
data_hopper2 = {
    "env": my_env,  # The simpy environment
    "name": "Hopper2",  # Name
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 1,
    "level": 0,
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
hopper2 = TransportProcessingResource(**data_hopper2)
data_hopper3 = {
    "env": my_env,  # The simpy environment
    "name": "Hopper3",  # Name
    "geometry": location_from_site,  # It starts at the "from site"
    "loading_rate": 1,  # Loading rate
    "unloading_rate": 1,  # Unloading rate
    "capacity": 1,
    "level": 0,
    "compute_v": compute_v_provider(5, 4.5),  # Variable speed
    "weekrate": 7,
}
hopper3 = TransportProcessingResource(**data_hopper3)
# data_hopper4 = {
#     "env": my_env,  # The simpy environment
#     "name": "Hopper4",  # Name
#     "geometry": location_from_site,  # It starts at the "from site"
#     "loading_rate": 1,  # Loading rate
#     "unloading_rate": 1,  # Unloading rate
#     "capacity": 1,
#     "level": 0,
#     "compute_v": compute_v_provider(5, 4.5),  # Variable speed
#     "weekrate": 7,
# }
# hopper4 = TransportProcessingResource(**data_hopper4)


#
# definition of loading a barge
registry = {}
cutter_list = [cutter1, cutter2]
for hopper in [hopper1, hopper2, hopper3]:
    first_cutter = cutter_list[0]
    cutter_list= cutter_list[1:]
    cutter_list.append(first_cutter)
    for cutter in cutter_list:
        requested_resources = {}
        run = []
        
        shift_amount_loading_data = {
            "env": my_env,  # The simpy environment defined in the first cel
            "name": "Load",  # We are moving soil
            "registry": registry,
            "processor": cutter,
            "origin": from_site,
            "destination": hopper,
            "amount": 1,
            "duration": 10,
            "requested_resources":requested_resources,
            "keep_resources":[hopper],
            "postpone_start": True,
        }
        run.append(model.ShiftAmountActivity(**shift_amount_loading_data))
        
        move_activity_to_harbor_data = {
            "env": my_env,  # The simpy environment defined in the first cel
            "name": "sailing full",  # We are moving soil
            "registry": registry,
            "mover": hopper,
            "destination": to_site,
            "requested_resources":requested_resources,
            "keep_resources":[hopper],
            "postpone_start": True,
        }
        run.append(model.MoveActivity(**move_activity_to_harbor_data))

        shift_amount_loading_data = {
            "env": my_env,  # The simpy environment defined in the first cel
            "name": "Unload",  # We are moving soil
            "registry": registry,
            "processor": hopper,
            "origin": hopper,
            "destination": to_site,
            "amount": 1,
            "duration": 10,
            "requested_resources":requested_resources,
            "keep_resources":[hopper],
            "postpone_start": True,
        }
        run.append(model.ShiftAmountActivity(**shift_amount_loading_data))
        
        move_activity_to_harbor_data = {
            "env": my_env,  # The simpy environment defined in the first cel
            "name": "sailing empty",  # We are moving soil
            "registry": registry,
            "mover": hopper,
            "destination": from_site,
            "requested_resources":requested_resources,
            "postpone_start": True,
        }
        run.append(model.MoveActivity(**move_activity_to_harbor_data))

        sequential_activity_data = {
            "env": my_env,
            "name": "run",
            "registry": registry,
            "sub_processes": run,
            "postpone_start": True,
        }
        sequential_activity = model.SequentialActivity(**sequential_activity_data)
        
        while_data = {
            "env": my_env,  # The simpy environment defined in the first cel
            "name": "run while",  # We are moving soil
            "registry": registry,
            "sub_process": sequential_activity,
            "condition_event": [{"type":"container", "concept": from_site, "state":"empty"}],
            "postpone_start": False,
        }
        run_activity = model.WhileActivity(**while_data)

my_env.run()

#%%
log_df = pd.DataFrame(cutter1.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data = data.drop_duplicates()

log2_df = pd.DataFrame(cutter2.log)
data2 = log2_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data2 = data2.drop_duplicates()

hopper1_log_df = pd.DataFrame(hopper1.log)
data_hopper1 = hopper1_log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data_hopper1 = data_hopper1.drop_duplicates()

hopper2_log_df = pd.DataFrame(hopper2.log)
data_hopper2 = hopper2_log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data_hopper2 = data_hopper2.drop_duplicates()

hopper3_log_df = pd.DataFrame(hopper3.log)
data_hopper3 = hopper3_log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data_hopper3 = data_hopper3.drop_duplicates()


