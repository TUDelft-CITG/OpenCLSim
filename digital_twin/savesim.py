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

    data_type is the object type: ship, site, crane, etc.
    data: is the dictionary that is used to fill the data_type
    """
    
    def __init__(self, data_type, data, *args, **kwargs):

        # This is the case for activities
        if data_type == model.Activity:
            self.data_type = "Activity"
            
            self.data = {"name": data["name"],
                         "id": data["id"],
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
                                             ID = data["id"],           # The id
                                             origin = origin,           # We originate from the from_site
                                             destination = destination, # And therefore travel to the to_site
                                             loader = loader,           # The benefit of a TSHD, all steps can be done
                                             mover = mover,             # The benefit of a TSHD, all steps can be done
                                             unloader = unloader))      # The benefit of a TSHD, all steps can be done

        return sites, equipment, activities, environment


class LogSaver:
    """
    LogSaver allow saving all logs as .csv files.
    
    Objects should be a list containing the activities, sites and equipment.
    The ID could be the ID that is saved to the .pkl file, entering an ID is optional.
    If location is "", the files will be saved in the current working directory.
    """ 

    def __init__(self, sites, equipment, activities, simulation_id = "", simulation_name = "", location = "", overwrite = False):
        """ Initialization """

        # Save all properties
        assert type(activities) == list
        self.activities = activities
        
        assert type(equipment) == list
        self.equipment = equipment

        assert type(sites) == list
        self.sites = sites

        # Save simulation id and simulation name
        self.simulation_id = simulation_id if simulation_id else str(uuid.uuid1())
        self.simulation_name = simulation_name if simulation_name else self.simulation_id

        # Define location to save files
        self.location = location

        if len(self.location) != 0 and self.location[-1] != "/":
            self.location += "/"

        # Finally save all items
        self.overwrite = overwrite
        self.save_all_logs()
    
    
    def save_all_logs(self):
        """
        Save all logs to a specified location.
        If location is "", the logs will be saved in the current working directory.

        A file is saved with unique events          -- events.csv
        A file is saved with unique objects         -- objects.csv
        A file is saved with unique simulations     -- simulations.csv
        
        A file is saved with equipment logs         -- equipment_log.csv
        A file is saved with energy use             -- energy_use.csv
        A file is saved with dredging spill info    -- dredging_spill.csv
        """

        # Obtain unique information on simulation
        # Check if folder already contains simulation information
        self.get_unique_simulations()

        # Obtain unique events and objects
        # Check if folder already contains simulation information
        try:
            self.unique_events = pd.read_csv(self.location + "events.csv")
        except FileNotFoundError:
            self.unique_events = pd.DataFrame.from_dict({"EventID": [],
                                                         "EventName": []})
        
        try:
            self.unique_objects = pd.read_csv(self.location + "objects.csv")
        except FileNotFoundError:
            self.unique_objects = pd.DataFrame.from_dict({"ObjectID": [],
                                                          "ObjectName": [],
                                                          "ObjectType": []})

        for vessel in self.equipment:
            self.get_unique_events(vessel)
            self.get_unique_objects(vessel, "Equipment")
        for site in self.sites:
            self.get_unique_events(site)
            self.get_unique_objects(site, "Location")
        for activity in self.activities:
            self.get_unique_events(activity)
            self.get_unique_objects(activity, "Activity")

        # Obtain generalized equipment log
        try:
            self.equipment_log = pd.read_csv(self.location + "equipment_log.csv")
        except FileNotFoundError:
            self.equipment_log = pd.DataFrame.from_dict({"SimulationID": [],
                                                         "ObjectID": [],
                                                         "Event": [],
                                                         "Starts": [],
                                                         "Stops": [],
                                                         "Value": [],
                                                         "Longitude start": [],
                                                         "Latitude start": [],
                                                         "Longitude stop": [],
                                                         "Latitude stop": []})

        for vessel in self.equipment:
            self.get_equipment_log(vessel)

        # Obtain energy use log
        try:
            self.energy_use = pd.read_csv(self.location + "energy_use.csv")
        except FileNotFoundError:
            self.energy_use = pd.DataFrame.from_dict({"SimulationID": [],
                                                      "ObjectID": [],
                                                      "Event": [],
                                                      "Value": []})

        for vessel in self.equipment:
            self.get_energy_use(vessel)

        # Finally, check if other simulations are already saved energy_use.csv
        # Append data are save new files
        self.energy_use.to_csv(self.location + "energy_use.csv", index = False)
        self.equipment_log.to_csv(self.location + "equipment_log.csv", index = False)
        self.unique_objects.to_csv(self.location + "objects.csv", index = False)
        self.unique_events.to_csv(self.location + "events.csv", index = False)
        self.unique_simulation.to_csv(self.location + "simulations.csv", index = False)
    

    def get_energy_use(self, item):
        """
        Create a generalized log of energy use
        """

        object_log = pd.DataFrame.from_dict(item.log)
        object_dict = {"SimulationID": [],
                       "ObjectID": [],
                       "EventID": [],
                       "Value": []}

        for i, message in enumerate(object_log["Message"]):
            for eventID in self.unique_events["EventID"]:
                if "Energy use" in message:
                    object_dict["SimulationID"].append(self.simulation_id)
                    object_dict["ObjectID"].append(item.id)
                    object_dict["EventID"].append(eventID)
                    object_dict["Value"].append(object_log["Value"][i])

        object_dict = pd.DataFrame.from_dict(object_dict)

        if len(self.energy_use["SimulationID"]) == 0:
            self.energy_use = object_dict
            
        elif not ((self.energy_use["SimulationID"] == self.simulation_id) & (self.energy_use["ObjectID"] == item.id)).any():
            self.energy_use = pd.concat([self.energy_use, object_dict], ignore_index = True)
        
        elif self.overwrite == True:
            drop_rows = []

            for i, row in enumerate((self.energy_use["SimulationID"] == self.simulation_id) & (self.energy_use["ObjectID"] == item.id)):
                if row == True:
                    drop_rows.append(i)
            
            self.energy_use = self.energy_use.drop(drop_rows, axis = 0)
            self.energy_use = pd.concat([self.energy_use, object_dict], ignore_index = True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")

    def get_dredging_spill(self, item):
        """
        Create a generalized log of dredging spill
        """

    
    def get_equipment_log(self, item):
        """
        Create a generalized equipment log
        """

        object_log = pd.DataFrame.from_dict(item.log)
        object_dict = {"SimulationID": [],
                       "ObjectID": [],
                       "EventID": [],
                       "Start": [],
                       "Stop": [],
                       "Value": [],
                       "Longitude start": [],
                       "Latitude start": [],
                       "Longitude stop": [],
                       "Latitude stop": []}

        for i, message in enumerate(object_log["Message"]):
            for j, event in enumerate(self.unique_events["EventName"]):

                if message == event + " start":
                    object_dict["SimulationID"].append(self.simulation_id)
                    object_dict["ObjectID"].append(item.id)
                    object_dict["EventID"].append(self.unique_events["EventID"][j])
                    object_dict["Start"].append(object_log["Timestamp"][i])
                    object_dict["Longitude start"].append(object_log["Geometry"][i].x)
                    object_dict["Latitude start"].append(object_log["Geometry"][i].y)
                
                elif message == event + " stop":
                    object_dict["Stop"].append(object_log["Timestamp"][i])
                    object_dict["Value"].append(object_log["Value"][i])
                    object_dict["Longitude stop"].append(object_log["Geometry"][i].x)
                    object_dict["Latitude stop"].append(object_log["Geometry"][i].y)

        object_dict = pd.DataFrame.from_dict(object_dict)
        durations = (object_dict["Stop"] - object_dict["Start"])
        durations_days = []
        
        for event in durations:
            durations_days.append(event.total_seconds() / 3600 / 24)

        object_dict["Duration"] = durations_days

        # Check if combination of simulation ID and object ID already exists
        if len(self.equipment_log["SimulationID"]) == 0:
            self.equipment_log = object_dict
            
        elif not ((self.equipment_log["SimulationID"] == self.simulation_id) & (self.equipment_log["ObjectID"] == item.id)).any():
            self.equipment_log = pd.concat([self.equipment_log, object_dict], ignore_index = True)
        
        elif self.overwrite == True:
            drop_rows = []

            for i, row in enumerate((self.equipment_log["SimulationID"] == self.simulation_id) & (self.equipment_log["ObjectID"] == item.id)):
                if row == True:
                    drop_rows.append(i)
            
            self.equipment_log = self.equipment_log.drop(drop_rows, axis = 0)
            self.equipment_log = pd.concat([self.equipment_log, object_dict], ignore_index = True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")

    
    def get_unique_objects(self, item, object_type):
        """
        Create a list of unique objects
        """

        if item.id not in list(self.unique_objects["ObjectID"]):
            self.unique_objects = self.unique_objects.append({"ObjectID": item.id, "ObjectName": item.name, "ObjectType": object_type}, ignore_index=True)
        
        elif self.overwrite == True:
            self.unique_objects = self.unique_objects[self.unique_objects["ID"] != item.id]
            self.unique_objects = self.unique_objects.append({"ObjectID": item.id, "ObjectName": item.name, "ObjectType": object_type}, ignore_index=True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")


    def get_unique_simulations(self):
        """
        Create a list of unique simulations
        """

        try:
            self.unique_simulation = pd.read_csv(self.location + "simulations.csv")

            if self.simulation_id not in list(self.unique_simulation["SimulationID"]):
                self.unique_simulation = self.unique_simulation.append({"SimulationID": self.simulation_id, "SimulationName": self.simulation_name}, ignore_index=True)
            
            elif self.overwrite == True:
                self.unique_simulation = self.unique_simulation[self.unique_simulation["SimulationID"] != self.simulation_id]
                self.unique_simulation = self.unique_simulation.append({"SimulationID": self.simulation_id, "SimulationName": self.simulation_name}, ignore_index=True)

            else:
                raise KeyError("Simulation ID or simulation name already exist. " + 
                               "If you wish to overwrite the existing data, set overwrite to True")
                    
        except FileNotFoundError:
            self.unique_simulation = {"SimulationID": [self.simulation_id],
                                      "SimulationName": [self.simulation_name]}

            self.unique_simulation = pd.DataFrame.from_dict(self.unique_simulation)

    
    def get_unique_events(self, item):
        """
        Create a list of unique events
        """

        log = pd.DataFrame.from_dict(item.log)
        events = list(log["Message"].unique())

        for event in events:
            event = event.replace(" start", "")
            event = event.replace(" stop", "")

            if event not in list(self.unique_events["EventName"]):
                self.unique_events = self.unique_events.append({"EventID": str(uuid.uuid1()), "EventName": event}, ignore_index=True)