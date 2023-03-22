"""
Tests for openclsim.critical_path.dependencies_from_simpy module
"""
import datetime as dt
import numpy as np

from openclsim.critical_path.dependencies_from_simpy_step import (
    AlteredStepEnv,
    DependenciesFromSimpy,
)


def test_altered_step_environment():
    """Test AlteredStepEnv."""
    my_env = AlteredStepEnv(initial_time=0)
    # do a simple timeout and another and assert what is logged
    def simple_timeout(duration, value):
        value = yield my_env.timeout(duration, value=value)

    my_env.process(simple_timeout(10, 'p10'))
    my_env.process(simple_timeout(15, 'p15'))
    my_env.run(until=30)
    assert len(my_env.data_step) == 6, "2 times 3 events expected to have been handled"
    assert len(my_env.data_cause_effect) == 4, "2 times 3 events expected to have been handled"


def test_connect_all_of_dependencies(simulation_2_barges_custom_env):
    """Test _connect_all_of_dependencies method."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    my_cp._connect_all_of_dependencies()
    assert len(my_cp.cause_effect_list) == 1257
    assert len(np.unique(my_cp.cause_effect_list)) == 1260


def test_get_dependency_list(simulation_2_barges_custom_env):
    """ Test get_dependency_list method."""
    import logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    dependency_list = my_cp.get_dependency_list()

    assert len(dependency_list) == 103, "103 dependencies expected"

    # check that all dependencies have zero time diff
    for dep in my_cp.dependency_list:
        t0 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[0]), 'end_time'].iloc[0]
        t1 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[1]), 'start_time'].iloc[0]
        assert t1-t0 == dt.timedelta(seconds=0), "dependencies have no len in time!"


def test_get_dependency_list_exclude_allof(simulation_2_barges_custom_env):
    """ Test get_dependency_list method."""
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)

    dependency_list = my_cp.get_dependency_list(connect_all_off=False)

    assert len(dependency_list) == 103, "103 dependencies expected"

    # check that all dependencies have zero time diff
    for dep in my_cp.dependency_list:
        t0 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[0]), 'end_time'].iloc[0]
        t1 = my_cp.recorded_activities_df.loc[
            (my_cp.recorded_activities_df.cp_activity_id == dep[1]), 'start_time'].iloc[0]
        assert t1-t0 == dt.timedelta(seconds=0), "dependencies have no len in time!"


def test_get_critical_path_df(simulation_2_barges_custom_env):
    """ Test get_critical_path_df method. """
    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 79, "79 critical activities expected"


def test_get_critical_path_df_simple_simulation(simulation_while_sequential):
    """ Test get_critical_path_df method. """
    my_cp = DependenciesFromSimpy(**simulation_while_sequential)
    critical_df = my_cp.get_critical_path_df()
    assert critical_df.is_critical.sum() == 149, "149 critical activities expected"


def temp_testing_motl():
    """ TO DELETE """
    from tests.conftest import demo_data, demo_data_simple
    simulation_2_barges_custom_env = demo_data(2, 100, AlteredStepEnv)
    import networkx as nx
    import pandas as pd
    import simpy
    import copy
    import numpy as np
    import logging
    from openclsim.plot.vessel_planning import get_gantt_chart
    from openclsim.plot.vessel_planning import get_gantt_chart
    import plotly.graph_objs as go


    def temp_visualisation(simulation_data, critical_df, out_name="gant_1"):
        data = get_gantt_chart(simulation_data['object_list'],
                               id_map=simulation_data['activity_list'],
                               static=True, critical_path_dataframe=critical_df)
        fig = go.Figure(**data)
        fig.show()
        fig.write_html(rf"D:\temp_files\{out_name}.html")


    logging.basicConfig(filename=r"D:\temp_files\templog.log",
                        filemode='a',)
    logging.getLogger().setLevel(logging.INFO)

    my_cp = DependenciesFromSimpy(**simulation_2_barges_custom_env)
    recorded_activities = my_cp.get_recorded_activity_df()
    critical_df = my_cp.get_critical_path_df()
    temp_visualisation(simulation_2_barges_custom_env, critical_df, out_name="gant_1")
    dict_lookup = {row.ActivityID: row.Activity for row in recorded_activities.itertuples()}

    # make a nice log that shows what causes what
    tree_input = my_cp.cause_effect_list
    id_t = 12
    object_instance = my_cp.step_logging_dataframe.loc[id_t, 'event_object']

    SEEN = []

    def __extract_openclsim_dependencies(tree_input, elem=None, level=0):
        """
        Extract the relevant (OpenCLSim) dependencies from the complete list
        of all Simpy dependencies.

        This function will walk through a dependency tree which is represented by
        list of tuples (e.g. [(1, 2), (2, 3), (2, 4))]). Each tuple contains two
        event - IDs and can be  seen a dependency with a cause (first element
        tuple) and effect (second and last element tuple).
        AlteredStepEnv registers all events, but we are only
        interested in events which are OpenClSim activities with duration,
        i.e. we are only interested in Timeout event with a _delay attribute > 0.
        This function keeps track filters the original input to a
        """
        if elem is None:
            elem = tree_input[0][0]

        object_instance = my_cp.step_logging_dataframe.loc[elem, 'event_object']

        # note that we have seen this one
        SEEN.append(elem)
        # print(len(SEEN))

        # get effects
        effects_this_elem = [tup[1] for tup in tree_input if tup[0] == elem]
        spaces_level_based = " " * level
        # log some stuff
        logging.info(f"{spaces_level_based} eid {elem} (type {type(object_instance)})"
                     f" {object_instance.__str__()} causes {effects_this_elem}")
        if type(object_instance) == simpy.events.Timeout:
            logging.info(f"{spaces_level_based} OpenCLSIM activity {dict_lookup[object_instance.value]}")
        elif type(object_instance) == simpy.events.AllOf:
            logging.info(f"{spaces_level_based} AllOf {object_instance.value}")
        else:
            pass


        if len(effects_this_elem) > 0:
            level += 1

        for effect_this_elem in effects_this_elem:
            # print(f"Effect {effect_this_elem} from {effects_this_elem}")
            __extract_openclsim_dependencies(tree_input, elem=effect_this_elem, level=level)

        return None

    __extract_openclsim_dependencies(tree_input)


    get_gantt_chart(simulation_2_barges_custom_env['object_list'],
                         critical_path_dataframe=critical_df,
                         id_map=simulation_2_barges_custom_env['activity_list'])