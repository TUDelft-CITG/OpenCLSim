#%%
import datetime, time
import platform

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy

# spatial libraries
import shapely.geometry
from simplekml import Kml, Style

# package(s) for data handling
import numpy as np

# digital twin package
import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot

# Additional import to save the initialization of the simulation
import openclsim.savesim as savesim


# Create simulation environment
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
from openclsim.model import shift_amount_process, partial


def __try_to_init_activity(my_env, activity, activity_log_class):
    try:
        process_control = activity
    except KeyError:
        return False

    id = "shift_amount"
    activity_log = activity_log_class(env=my_env, name=id)

    process = my_env.process(process_control(activity_log=activity_log, env=my_env))

    return {"activity_log": activity_log, "process": process}


activity_log_class = type("ActivityLog", (core.Log, core.Identifiable), {})

activity = partial(
    shift_amount_process,
    processor=hopper,
    origin=from_site,
    destination=hopper,
    amount=2,
)

activity2 = partial(
    shift_amount_process,
    processor=hopper,
    origin=hopper,
    destination=to_site,
    amount=2,
)

res1 = __try_to_init_activity(my_env, activity, activity_log_class)
res2 = __try_to_init_activity(my_env, activity2, activity_log_class)

my_env.run(until=100)

log = res1['activity_log']
# %%
# Create activity
activity = model.Activity(
    env=my_env,  # The simpy environment defined in the first cel
    name="Soil movement",  # We are moving soil
    ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    origin=from_site,  # We originate from the from_site
    destination=to_site,  # And therefore travel to the to_site
    loader=hopper,  # The benefit of a TSHD, all steps can be done
    mover=hopper,  # The benefit of a TSHD, all steps can be done
    unloader=hopper,  # The benefit of a TSHD, all steps can be done
    start_event=None,  # We can start right away
    stop_event=None,
)  # We stop once there is nothing more to move

# %%
my_env.run()

print("")
print(
    "*** Dredging project finished in {}".format(
        datetime.timedelta(seconds=int(my_env.now - my_env.epoch))
    )
)
print("*** Installation cost {:,.2f}€.".format(int(hopper.cost)))


# %%
vessels = [hopper]

activities = ["loading", "unloading", "sailing filled", "sailing empty"]
colors = {
    0: "rgb(55,126,184)",
    1: "rgb(255,150,0)",
    2: "rgb(98, 192, 122)",
    3: "rgb(98, 141, 122)",
}

plot.vessel_planning(vessels, activities, colors)
