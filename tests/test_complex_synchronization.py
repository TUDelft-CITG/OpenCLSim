"""Test package."""
import simpy

import openclsim.model as model

from .test_utils import assert_log


def test_complex_synchronization():
    """Test complex synchronization."""
    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)
    registry = {}
    keep_resources = {}

    reporting_activity = model.BasicActivity(
        env=my_env,
        name="Reporting activity",
        ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
        registry=registry,
        duration=0,
        postpone_start=False,
        keep_resources=keep_resources,
    )

    sub_processes = [
        model.BasicActivity(
            env=my_env,
            name="A Basic activity1",
            ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
            registry=registry,
            duration=14,
            postpone_start=True,
            additional_logs=[reporting_activity],
            keep_resources=keep_resources,
        ),
        model.BasicActivity(
            env=my_env,
            name="A Basic activity2",
            ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
            registry=registry,
            duration=10,
            additional_logs=[reporting_activity],
            postpone_start=True,
            keep_resources=keep_resources,
        ),
        model.BasicActivity(
            env=my_env,
            name="A Basic activity3",
            ID="6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
            registry=registry,
            duration=220,
            additional_logs=[reporting_activity],
            postpone_start=True,
            keep_resources=keep_resources,
            start_event=[
                {"type": "activity", "name": "B Basic activity2", "state": "done"}
            ],
        ),
    ]

    sub_processes2 = [
        model.BasicActivity(
            env=my_env,
            name="B Basic activity1",
            ID="5dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
            registry=registry,
            duration=1,
            postpone_start=True,
            additional_logs=[reporting_activity],
            keep_resources=keep_resources,
        ),
        model.BasicActivity(
            env=my_env,
            name="B Basic activity2",
            ID="5dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
            registry=registry,
            duration=500,
            additional_logs=[reporting_activity],
            postpone_start=True,
            keep_resources=keep_resources,
        ),
        model.BasicActivity(
            env=my_env,
            name="B Basic activity3",
            ID="5dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
            registry=registry,
            duration=120,
            additional_logs=[reporting_activity],
            postpone_start=True,
            keep_resources=keep_resources,
        ),
    ]

    model.SequentialActivity(
        env=my_env,
        name="B Sequential process",
        ID="5dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
        registry=registry,
        sub_processes=sub_processes2,
        keep_resources=keep_resources,
    )

    model.SequentialActivity(
        env=my_env,
        name="A Sequential process",
        ID="6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
        registry=registry,
        sub_processes=sub_processes,
        keep_resources=keep_resources,
    )

    my_env.run()

    assert my_env.now == 721
    assert_log(reporting_activity.log)
