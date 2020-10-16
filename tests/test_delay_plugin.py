"""Test package."""

import datetime

import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model
import openclsim.plugins as plugins

from .test_utils import parse_log


def test_delay_plugin():
    """Test the delay plugin."""
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}

    # The generic site class
    Site = type(
        "Site",
        (
            core.Identifiable,
            core.Log,
            core.Locatable,
            core.HasContainer,
            core.HasResource,
        ),
        {},
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5d",
        "geometry": location_from_site,
        "capacity": 12,
        "level": 12,
    }

    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)

    data_to_site = {
        "env": my_env,
        "name": "Dumplocatie",
        "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5c",
        "geometry": location_to_site,
        "capacity": 12,
        "level": 0,
    }

    from_site = Site(**data_from_site)
    to_site = Site(**data_to_site)

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.HasResource,
            core.LoadingFunction,
            core.UnloadingFunction,
        ),
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: 10

    # TSHD variables
    data_hopper = {
        "env": my_env,
        "name": "Hopper 01",
        "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",
        "geometry": location_from_site,
        "loading_rate": 1,
        "unloading_rate": 1,
        "capacity": 4,
        "compute_v": compute_v_provider(5, 4.5),
    }

    hopper = TransportProcessingResource(**data_hopper)

    DelaySequenceActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.SequentialActivity), {}
    )

    DelayWhileActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.WhileActivity), {}
    )

    DelayMoveActivity = type(
        "TestMoveActivity", (plugins.HasDelayPlugin, model.MoveActivity), {}
    )

    DelayShiftActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.ShiftAmountActivity), {}
    )

    DelayBasicActivity = type(
        "TestShiftActivity", (plugins.HasDelayPlugin, model.BasicActivity), {}
    )

    single_run = []

    move_activity_to_harbor_data = {
        "env": my_env,
        "name": "sailing empty",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
        "registry": registry,
        "mover": hopper,
        "destination": from_site,
        "postpone_start": True,
        "delay_percentage": 10,
    }
    single_run.append(DelayMoveActivity(**move_activity_to_harbor_data))

    shift_amount_activity_loading_data = {
        "env": my_env,
        "name": "Transfer MP",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
        "registry": registry,
        "processor": hopper,
        "origin": from_site,
        "destination": hopper,
        "amount": 4,
        "duration": 10,
        "postpone_start": True,
        "delay_percentage": 10,
    }
    single_run.append(DelayShiftActivity(**shift_amount_activity_loading_data))

    move_activity_to_site_data = {
        "env": my_env,
        "name": "sailing filler",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
        "registry": registry,
        "mover": hopper,
        "destination": to_site,
        "postpone_start": True,
        "delay_percentage": 10,
    }
    single_run.append(DelayMoveActivity(**move_activity_to_site_data))

    shift_amount_activity_unloading_data = {
        "env": my_env,
        "name": "Transfer TP",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
        "registry": registry,
        "processor": hopper,
        "origin": hopper,
        "destination": to_site,
        "amount": 4,
        "duration": 10,
        "postpone_start": True,
        "delay_percentage": 10,
    }
    single_run.append(DelayShiftActivity(**shift_amount_activity_unloading_data))

    basic_activity_data = {
        "env": my_env,
        "name": "Basic activity",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
        "registry": registry,
        "duration": 0,
        "additional_logs": [hopper],
        "postpone_start": True,
        "delay_percentage": 10,
    }
    single_run.append(DelayBasicActivity(**basic_activity_data))

    sequential_activity_data = {
        "env": my_env,
        "name": "Single run process",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",
        "registry": registry,
        "sub_processes": single_run,
        "postpone_start": True,
        "delay_percentage": 10,
    }
    activity = DelaySequenceActivity(**sequential_activity_data)

    expr = [{"type": "container", "concept": to_site, "state": "full"}]
    while_data = {
        "env": my_env,
        "name": "while",
        "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        "registry": registry,
        "sub_process": activity,
        "condition_event": expr,
        "postpone_start": False,
        "delay_percentage": 10,
    }
    while_activity = DelayWhileActivity(**while_data)

    my_env.run()

    hopper_benchmark = {
        "Message": [
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Basic activity",
            "Basic activity",
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Basic activity",
            "Basic activity",
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "move activity sailing empty of Hopper 01 to Winlocatie",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "Shift amount activity Transfer MP transfer default from Winlocatie to Hopper 01 with Hopper 01",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "move activity sailing filler of Hopper 01 to Dumplocatie",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Shift amount activity Transfer TP transfer default from Hopper 01 to Dumplocatie with Hopper 01",
            "Basic activity",
            "Basic activity",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
            datetime.datetime(1970, 1, 1, 0, 0, 10),
            datetime.datetime(1970, 1, 1, 0, 0, 11),
            datetime.datetime(1970, 1, 1, 0, 15, 53, 824591),
            datetime.datetime(1970, 1, 1, 0, 17, 28, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 28, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 38, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 38, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 35, 7, 842347),
            datetime.datetime(1970, 1, 1, 0, 36, 42, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 42, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 52, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 52, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 53, 124806),
            datetime.datetime(1970, 1, 1, 0, 52, 35, 949397),
            datetime.datetime(1970, 1, 1, 0, 54, 10, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 10, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 20, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 20, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 1, 13, 33, 677858),
            datetime.datetime(1970, 1, 1, 1, 15, 7, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 7, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 17, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 17, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 18, 960317),
            datetime.datetime(1970, 1, 1, 1, 31, 1, 784908),
            datetime.datetime(1970, 1, 1, 1, 32, 36, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 36, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 46, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 46, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
        ],
        "Value": [
            0.0,
            0.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            0,
            0,
            0.0,
            0.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            0,
            0,
            0.0,
            0.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            4.0,
            0,
            0,
        ],
        "Geometry": [
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            None,
            None,
            (4.25222222, 52.11428333),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            None,
            None,
            (4.25222222, 52.11428333),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.18055556, 52.18664444),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            (4.25222222, 52.11428333),
            None,
            None,
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff52",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff54",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5h",
        ],
        "ActivityState": [
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
            "START",
            "START",
            "STOP",
            "STOP",
            "START",
            "STOP",
        ],
    }

    while_benchmark = {
        "Message": [
            "conditional process while",
            "sub process Single run process",
            "sequential Single run process",
            "sub process sailing empty",
            "sub process sailing empty",
            "sub process Transfer MP",
            "sub process Transfer MP",
            "sub process sailing filler",
            "sub process sailing filler",
            "sub process Transfer TP",
            "sub process Transfer TP",
            "sub process Basic activity",
            "sub process Basic activity",
            "delay and downtime Sequence activity Single run process",
            "delay and downtime Sequence activity Single run process",
            "sequential Single run process",
            "sub process Single run process",
            "sub process Single run process",
            "sequential Single run process",
            "sub process sailing empty",
            "sub process sailing empty",
            "sub process Transfer MP",
            "sub process Transfer MP",
            "sub process sailing filler",
            "sub process sailing filler",
            "sub process Transfer TP",
            "sub process Transfer TP",
            "sub process Basic activity",
            "sub process Basic activity",
            "delay and downtime Sequence activity Single run process",
            "delay and downtime Sequence activity Single run process",
            "sequential Single run process",
            "sub process Single run process",
            "sub process Single run process",
            "sequential Single run process",
            "sub process sailing empty",
            "sub process sailing empty",
            "sub process Transfer MP",
            "sub process Transfer MP",
            "sub process sailing filler",
            "sub process sailing filler",
            "sub process Transfer TP",
            "sub process Transfer TP",
            "sub process Basic activity",
            "sub process Basic activity",
            "delay and downtime Sequence activity Single run process",
            "delay and downtime Sequence activity Single run process",
            "sequential Single run process",
            "sub process Single run process",
            "delay and downtime While activity while",
            "delay and downtime While activity while",
            "conditional process while",
        ],
        "Timestamp": [
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0),
            datetime.datetime(1970, 1, 1, 0, 0, 11),
            datetime.datetime(1970, 1, 1, 0, 0, 11),
            datetime.datetime(1970, 1, 1, 0, 17, 28, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 28, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 17, 39, 107050),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 19, 25, 17755),
            datetime.datetime(1970, 1, 1, 0, 36, 42, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 42, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 53, 124806),
            datetime.datetime(1970, 1, 1, 0, 36, 53, 124806),
            datetime.datetime(1970, 1, 1, 0, 54, 10, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 10, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 54, 21, 231856),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 0, 57, 50, 853266),
            datetime.datetime(1970, 1, 1, 1, 15, 7, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 7, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 18, 960317),
            datetime.datetime(1970, 1, 1, 1, 15, 18, 960317),
            datetime.datetime(1970, 1, 1, 1, 32, 36, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 36, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
            datetime.datetime(1970, 1, 1, 1, 32, 47, 67367),
            datetime.datetime(1970, 1, 1, 1, 36, 16, 688777),
            datetime.datetime(1970, 1, 1, 1, 36, 16, 688777),
            datetime.datetime(1970, 1, 1, 1, 36, 16, 688777),
            datetime.datetime(1970, 1, 1, 1, 36, 16, 688777),
            datetime.datetime(1970, 1, 1, 1, 45, 54, 357655),
            datetime.datetime(1970, 1, 1, 1, 45, 54, 357655),
        ],
        "Value": [
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
        ],
        "Geometry": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "ActivityID": [
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
            "6dbbbdf7-4589-11e9-bf3b-b469212bff5g",
        ],
        "ActivityState": [
            "START",
            "START",
            "START",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "WAIT_START",
            "WAIT_STOP",
            "STOP",
            "STOP",
            "START",
            "START",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "WAIT_START",
            "WAIT_STOP",
            "STOP",
            "STOP",
            "START",
            "START",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "START",
            "STOP",
            "WAIT_START",
            "WAIT_STOP",
            "STOP",
            "STOP",
            "WAIT_START",
            "WAIT_STOP",
            "STOP",
        ],
    }

    assert parse_log(while_activity.log) == while_benchmark
    assert parse_log(hopper.log) == hopper_benchmark
