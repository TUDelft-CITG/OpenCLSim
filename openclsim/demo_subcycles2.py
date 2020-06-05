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
import uuid

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
    "ID": str(uuid.uuid4()),  # For logging purposes
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
    "ID": str(uuid.uuid4()),  # For logging purposes
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
    "ID": str(uuid.uuid4()),  # For logging purposes
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

#
# definition of loading
#
registry = {}
loading = []

basic_activity_data1= {"env"  : my_env,
                      "name" : "MP loading hook on rigging",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 45,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
loading.append(model.BasicActivity(**basic_activity_data1))

shift_amount_loading_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer MP",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "processor": hopper,
    "origin": from_site,
    "destination": hopper,
    "amount": 1,
    "duration": 120,
    "id_": "MP",
    "postpone_start": True,
}
activity_mp_loading = model.ShiftAmountActivity(**shift_amount_loading_data)
activity_mp_loading_seq_data = {
    "env": my_env,
    "name": "loading MP seq",
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_processes": [activity_mp_loading],
    "postpone_start": True,
}
activity_mp_loading_seq = model.SequentialActivity(**activity_mp_loading_seq_data)
while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "loading MP while",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_process": activity_mp_loading_seq,
    "condition_event": [{"or":[{"type":"container", "concept": hopper, "state":"full", "id_":"MP"},
                                {"type":"container", "concept": from_site, "state":"empty", "id_":"MP"}]
                        }],
    #"condition_event": [{"type":"container", "concept": hopper, "state":"full", "id_":"MP"}],
    "postpone_start": True,
}
loading.append(model.WhileActivity(**while_data))

basic_activity_data2= {"env"  : my_env,
                      "name" : "MP loading hook off rigging",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 15,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
loading.append(model.BasicActivity(**basic_activity_data2))

basic_activity_data3= {"env"  : my_env,
                      "name" : "TP loading hook on rigging",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 30,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
loading.append(model.BasicActivity(**basic_activity_data3))

shift_amount_loading_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Transfer TP",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "processor": hopper,
    "origin": from_site,
    "destination": hopper,
    "amount": 1,
    "duration": 10,
    "id_": "TP",
    "postpone_start": True,
}
activity_tp_loading = model.ShiftAmountActivity(**shift_amount_loading_data2)
activity_tp_loading_seq_data = {
    "env": my_env,
    "name": "loading MP seq",
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_processes": [activity_tp_loading],
    "postpone_start": True,
}
activity_tp_loading_seq = model.SequentialActivity(**activity_tp_loading_seq_data)
while_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "loading MP while",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_process": activity_tp_loading_seq,
    "condition_event": [{"or":[{"type":"container", "concept": hopper, "state":"full", "id_":"TP"},
                                {"type":"container", "concept": from_site, "state":"empty", "id_":"TP"}]
                          }],
    #"condition_event": [{"type":"container", "concept": hopper, "state":"full", "id_":"TP"}],
    "postpone_start": True,
}
loading.append(model.WhileActivity(**while_data2))

basic_activity_data4= {"env"  : my_env,
                      "name" : "TP loading hook off rigging",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 15,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
loading.append(model.BasicActivity(**basic_activity_data4))

sequential_activity_data1 = {
    "env": my_env,
    "name": "loading",
    "ID": str(uuid.uuid4()),  # For logging purposes"registry": registry,
    "registry": registry,
    "sub_processes": loading,
    "postpone_start": True,
}

loading_activity = model.SequentialActivity(**sequential_activity_data1)


#
# definition of unloading
#
unloading = []
move_activity_transit_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "sailing transit",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "mover": hopper,
    "destination": to_site,
    "postpone_start": True,
}
unloading.append(model.MoveActivity(**move_activity_transit_data))
basic_activity_data20= {"env"  : my_env,
                      "name" : "MP preparing for installation",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 45,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
unloading.append(model.BasicActivity(**basic_activity_data20))
shift_amount_unloading_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Install MP",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "processor": hopper,
    "origin": hopper,
    "destination": to_site,
    "amount": 1,
    "duration": 120,
    "id_": "MP",
    "postpone_start": True,
}
unloading.append(model.ShiftAmountActivity(**shift_amount_unloading_data))
basic_activity_data21= {"env"  : my_env,
                      "name" : "Installing MP",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 45,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
unloading.append(model.BasicActivity(**basic_activity_data21))
basic_activity_data22= {"env"  : my_env,
                      "name" : "Prepare TP installation",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 45,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
unloading.append(model.BasicActivity(**basic_activity_data22))

shift_amount_unloading_data2 = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "Install TP",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "processor": hopper,
    "origin": hopper,
    "destination": to_site,
    "amount": 1,
    "duration": 120,
    "id_": "TP",
    "postpone_start": True,
}
unloading.append(model.ShiftAmountActivity(**shift_amount_unloading_data2))

basic_activity_data23= {"env"  : my_env,
                      "name" : "TP finalize installation",
                      "registry": registry,
                      "ID":str(uuid.uuid4()),  # For logging purposes
                      "duration" : 45,
                      "additional_logs": [hopper],
                      "postpone_start": True,
                      }
unloading.append(model.BasicActivity(**basic_activity_data23))


sequential_activity_data2 = {
    "env": my_env,
    "name": "unloading",
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_processes": unloading,
    "postpone_start": True,
}
sequential_activity = model.SequentialActivity(**sequential_activity_data2)

while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "unloading while",  # We are moving soil
    "ID":str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_process": sequential_activity,
    # "condition_event": [from_site.container.get_empty_event, to_site.container.get_full_event],
    # "condition_event": my_env.all_of(events=[to_site.container.get_full_event(id_="MP"),to_site.container.get_full_event(id_="TP")]),
    "condition_event": [{"or":[{"type":"container", "concept": to_site, "state":"full", "id_":"TP"},
                                {"type":"container", "concept": hopper, "state":"empty", "id_":"TP"}]
                          }],
    #"condition_event": [{"type":"container", "concept": hopper, "state":"empty", "id_":"TP"}],
    "postpone_start": True,
}
unloading_activity = model.WhileActivity(**while_data)



#
# definition of main cycle

single_run = []

move_activity_to_harbor_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "sailing empty",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "mover": hopper,
    "destination": from_site,
    "postpone_start": True,
}
single_run.append(model.MoveActivity(**move_activity_to_harbor_data))

single_run.append(loading_activity)

move_activity_to_site_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "sailing filled",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "mover": hopper,
    "destination": to_site,
    "postpone_start": True,
}
single_run.append(model.MoveActivity(**move_activity_to_site_data))

single_run.append(unloading_activity)

sequential_activity_data3 = {
    "env": my_env,
    "name": "Single run process",
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_processes": single_run,
    "postpone_start": True,
}
activity = model.SequentialActivity(**sequential_activity_data3)

while_data = {
    "env": my_env,  # The simpy environment defined in the first cel
    "name": "single run while",  # We are moving soil
    "ID": str(uuid.uuid4()),  # For logging purposes
    "registry": registry,
    "sub_process": activity,
    # "condition_event": [from_site.container.get_empty_event, to_site.container.get_full_event],
    # "condition_event": my_env.all_of(events=[to_site.container.get_full_event(id_="MP"),to_site.container.get_full_event(id_="TP")]),
    "condition_event": [{"type":"container", "concept": to_site, "state":"full", "id_":"TP"}],
    "postpone_start": False,
}
while_activity = model.WhileActivity(**while_data)

my_env.run()

log_df = pd.DataFrame(hopper.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data = data.drop_duplicates()
data = data[data['ActivityState']=='START']

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
    f"from_site :{from_site.container.get_level(id_='MP')}MPs and {from_site.container.get_level(id_='TP')}TPs "
)
c = to_site.container
ee = c.get_full_event(id_="MP")
ee = c.full_event

#%%
ee = activity.parse_expression([{"or":[{"type":"container", "concept": hopper, "state":"full", "id_":"TP"},
                               {"type":"container", "concept": from_site, "state":"empty", "id_":"TP"}]}])
my_env.timeout(1)
#%%
ee = activity.parse_expression([{"type":"container", "concept": hopper, "state":"full", "id_":"TP"}])
my_env.timeout(1)
