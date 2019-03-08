import pandas as pd
import numpy as np

import datetime
import time

import uuid
import simpy

import dill as pickle

import digital_twin.model as model

class ToSave:
    """
    Class that defines objects that have to be saved.
    """
    
    def __init__(self, data_type, data, *args, **kwargs):

        # This is the case for activities
        if data_type == model.Activity:
            self.data_type = "Activity"
            
            self.data = {"name": data["name"],
                         "mover": data["mover"].name,
                         "loader": data["loader"].name,
                         "unloader": data["unloader"].name,
                         "origin": data["origin"].name,
                         "destination": data["destination"].name,
                         "stop_condition": None, #data["stop_condition"],
                         "start_condition": None, #data["start_condition"],
                         "condition": None} #data["condition"]}
        
        # This is the case for equipment and sites
        elif type(data_type) == type:
            self.data_type = []

            for subclass in data_type.__mro__:
                if subclass.__module__ == "digital_twin.core" and subclass.__name__ not in ["Identifiable", "Log", "SimpyObject"] :
                    self.data_type.append(subclass.__name__)
            
            self.data = data
            self.data["env"] = None


class SimulationSave:
    """
    SimulationSave allows save all obtained data.

    Environment: The simpy environment
    Activities:  List element with 'ToSave' classes of all unique activities
    Equipment:   List element with 'ToSave' classes of all unique pieces of equipment
    Sites:       List element with 'ToSave' classes of all unique sites
    """

    def __init__(self, environment, activities, equipment, sites, *args, **kwargs):
        """ Initialization """

        # Generate unique ID for the simulation
        self.id = str(uuid.uuid1())

        # Save the environment
        #assert type(environment) == simpy.core.Environment
        self.simulation_start = environment.now

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
        
        return {"ID": self.id,
                "Simulation start": self.simulation_start,
                "Activities": self.activities,
                "Equipment": self.equipment,
                "Sites": self.sites}
        
    
    def save_ini_file(self, filename, location = ""):
        """
        For all items of the simulation, save the properties and generate an initialization file.
        This file should be a JSON format and readable to start a new simulation.

        If location is "", the init will be saved in the current working directory.
        """

        if len(location) != 0 and location[-1] != "/":
            location += "/"

        file_name = location + filename + ".pkl"

        with open(file_name, 'wb') as file:
            pickle.dump(self.init, file)
    

class SimulationOpen:
    """
    SimulationOpen allows to define simulations from .pkl files.
    
    If location is "", the init will be saved in the current working directory.
    """ 

    def __init__(self, file_name):
        """ Initialization """

        self.simulation = self.open_ini_file(file_name)

    def open_ini_file(self, file_name):
        """
        For all items of the simulation, save the properties and generate an initialization file.
        This file should be a JSON format and readable to start a new simulation.

        If location is "", the init will be saved in the current working directory.
        """

        with open(file_name, 'rb') as file:
            return pickle.load(file)
    
    def extract_files(self):
        environment = simpy.Environment(initial_time = self.simulation["Simulation start"])
        environment.epoch = time.mktime(datetime.datetime.fromtimestamp(self.simulation["Simulation start"]).timetuple())

        sites = []
        equipment = []

        for site in self.simulation["Sites"]:
            site_object = model.get_class_from_type_list("Site", site.data_type)
            site.data["env"] = environment
            
            sites.append(site_object(**site.data))

        for ship in self.simulation["Equipment"]:
            ship_object = model.get_class_from_type_list("Ship", ship.data_type)
            ship.data["env"] = environment
            
            equipment.append(ship_object(**ship.data))
        
        activities = []

        for activity in self.simulation["Activities"]:
            data = activity.data
            
            mover = [ i for i in equipment if i.name == data["mover"] ][0]
            loader = [ i for i in equipment if i.name == data["loader"] ][0]
            unloader = [ i for i in equipment if i.name == data["unloader"] ][0]
            
            origin = [ i for i in sites if i.name == data["origin"] ][0]
            destination = [ i for i in sites if i.name == data["destination"] ][0]
            
            activities.append(model.Activity(env = environment,         # The simpy environment defined in the first cel
                                             name = data["name"],       # We are moving soil
                                             origin = origin,           # We originate from the from_site
                                             destination = destination, # And therefore travel to the to_site
                                             loader = loader,           # The benefit of a TSHD, all steps can be done
                                             mover = mover,             # The benefit of a TSHD, all steps can be done
                                             unloader = unloader))      # The benefit of a TSHD, all steps can be done

        return sites, equipment, activities, environment


class LogSaver():
    """
    """

    def __init__():
        pass
    
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