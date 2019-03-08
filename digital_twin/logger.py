import pandas as pd
import numpy as np

import uuid
import simpy

import dill
import pickle


class ToSave:
    """
    Class that defines objects that have to be saved.
    """
    
    def __init__(self, data_type, data, *args, **kwargs):
        self.type = data_type
        self.data = data

        self.data["env"] = None


class DataExtraction:
    """
    DataExtraction allows save all obtained data.

    Environment: The simpy environment
    Activities:  List element with 'ToSave' classes of all unique activities
    Equipment:   List element with 'ToSave' classes of all unique pieces of equipment
    Sites:       List element with 'ToSave' classes of all unique sites
    """

    def __init__(self, environment, activities, equipment, sites,
                 *args, **kwargs):

        # Generate unique ID for the simulation
        self.id = str(uuid.uuid1())

        # Save the environment
        #assert type(environment) == simpy.core.Environment
        self.environment = environment
        self.start = environment.now

        # Save all properties
        assert type(activities) == list
        self.activities = activities
        
        assert type(equipment) == list
        self.equipment = equipment

        assert type(sites) == list
        self.sites = sites

        # Save the initialization properties
        self.init = self.init_properties


    @property
    def init_properties(self):
        """
        Save all properties of the simulation
        """

        simulation_setup = {"Environment": self.environment,
                            "Activities": self.activities,
                            "Equipment": self.equipment,
                            "Sites": self.sites}
        
        return pickle.dumps(simulation_setup)

    
    def save_ini_file(self, location = ""):
        """
        For all items of the simulation, save the properties and generate an initialization file.
        This file should be a JSON format and readable to start a new simulation.

        If location is "", the init will be saved in the current working directory.
        """

        file_name = location + self.id

    
    def save_all_logs(self, location = ""):
        """
        Save all logs to a specified location.
        If location is "", the logs will be saved in the current working directory.
        """

        file_name = location + self.id

        for activity in self.activities:
            pd.DataFrame.from_dict(activity.log).to_csv(file_name + activity.name)
        for piece in self.equipment:
            pd.DataFrame.from_dict(piece.log).to_csv(file_name + piece.name)
        for site in self.sites:
            pd.DataFrame.from_dict(site.log).to_csv(file_name + site.name)