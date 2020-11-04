"""Test package."""

import datetime

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_mulitcontainer():
    """Test the multicontainer."""
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
            core.LoadingFunction,  # Add a loading function
            core.UnloadingFunction,  # Add an unloading function
        ),
        {},
    )

    # For more realistic simulation you might want to have speed dependent on the volume carried by the vessel
    def compute_v_provider(v_empty, v_full):
        return lambda x: 10

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
        "postpone_start": False,
    }
    activity = model.ShiftAmountActivity(**shift_amount_activity_loading_data)

    my_env.run()

    assert my_env.now == 20
    assert hopper.container.get_level(id_="MP") == 1
    assert hopper.container.get_level(id_="TP") == 0
    assert from_site.container.get_level(id_="TP") == 0
    assert from_site.container.get_level(id_="MP") == 1

    assert_log(hopper.log)
    assert_log(activity.log)
    assert_log(from_site.log)
