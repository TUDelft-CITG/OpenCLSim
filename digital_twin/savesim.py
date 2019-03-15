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
        self.id = simulation_id if simulation_id else str(uuid.uuid1())
        self.name = simulation_name if simulation_name else self.id

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

        A file is saved with unique events             -- events.csv
        A file is saved with unique location objects   -- locations.csv
        A file is saved with unique equipment objects  -- equipment.csv
        A file is saved with unique activity objects   -- activities.csv
        A file is saved with unique simulations        -- simulations.csv
        
        A file is saved with equipment logs            -- equipment_log.csv
        A file is saved with energy use                -- energy_use.csv
        A file is saved with dredging spill info       -- dredging_spill.csv
        """

        # First get all unique properties
        # Obtain information on simulations
        simulation_dict = {"SimulationID": [], "SimulationName": []}
        self.get_unique_properties("simulations", simulation_dict)

        # Obtain information on activities
        activity_dict = {"ActivityID": [], "ActivityName": []}
        self.get_unique_properties("activities", activity_dict)
        
        # Obtain information on equipment
        equipment_dict = {"EquipmentID": [], "EquipmentName": []}
        self.get_unique_properties("equipment", equipment_dict)

        # Obtain information on locations
        location_dict = {"LocationID": [], "LocationName": [], "Longitude": [], "Latitude": []}
        self.get_unique_properties("location", location_dict)

        # Obtain information on events
        event_dict = {"EventID": [], "EventName": []}
        self.get_unique_properties("events", event_dict)

        
        # Continue with obtaining the logs, energy use and dredging spill
        self.get_equipment_log()
        self.get_energy()
        self.get_spill()

        # Save all as csv files
        self.dredging_spill.to_csv(self.location + "dredging_spill.csv", index = False)
        self.energy_use.to_csv(self.location + "energy_use.csv", index = False)
        self.equipment_log.to_csv(self.location + "equipment_log.csv", index = False)
        self.unique_events.to_csv(self.location + "events.csv", index = False)
        self.unique_activities.to_csv(self.location + "activities.csv", index = False)
        self.unique_equipment.to_csv(self.location + "equipment.csv", index = False)
        self.unique_locations.to_csv(self.location + "locations.csv", index = False)
        self.unique_simulations.to_csv(self.location + "simulations.csv", index = False)

    def get_unique_properties(self, object_type, object_dict):
        """
        Obtain unique properties for the given list
        """

        try:
            unique_df = pd.read_csv(self.location + object_type + ".csv")
        except FileNotFoundError:
            unique_df = pd.DataFrame.from_dict(object_dict)

        if object_type == "simulations":
            self.unique_simulations = self.append_dataframe(unique_df, self, "Simulation")
        
        elif object_type == "activities":
            for activity in self.activities:
                unique_df = self.append_dataframe(unique_df, activity, "Activity")
            
            self.unique_activities = unique_df
        
        elif object_type == "equipment":
            for piece in self.equipment:
                unique_df = self.append_dataframe(unique_df, piece, "Equipment")
            
            self.unique_equipment = unique_df

        elif object_type == "events":
            for piece in self.equipment:                
                unique_df = self.event_dataframe(unique_df, piece)
            
            self.unique_events = unique_df
        
        elif object_type == "location":
            for site in self.sites:
                unique_df = self.append_dataframe(unique_df, site, "Location")
            
            self.unique_locations = unique_df


    def append_dataframe(self, existing_df, object_id, object_type):
        """
        Check if dataframe is alfready filled with information, if not append.
        If it is filled with similar values, raise an error unless self.overwrite == True.
        """

        if object_id.id not in list(existing_df[object_type + "ID"]):
            if object_type != "Location":
                existing_df = existing_df.append({object_type + "ID": object_id.id, object_type + "Name": object_id.name}, ignore_index=True)
            else:
                existing_df = existing_df.append({object_type + "ID": object_id.id, object_type + "Name": object_id.name,
                                                  "Longitude": object_id.geometry.x, "Latitude": object_id.geometry.y}, ignore_index=True)
            
        elif self.overwrite == True:
            existing_df = existing_df[existing_df[object_type + "ID"] != object_id.id]

            if object_type != "Location":
                existing_df = existing_df.append({object_type + "ID": object_id.id, object_type + "Name": object_id.name}, ignore_index=True)
            else:
                existing_df = existing_df.append({object_type + "ID": object_id.id, object_type + "Name": object_id.name,
                                                  "Longitude": object_id.geometry.x, "Latitude": object_id.geometry.y}, ignore_index=True)

        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                            "If you wish to overwrite the existing data, set overwrite to True")
        
        return existing_df

    
    def event_dataframe(self, existing_df, piece):
        """
        Check if dataframe is alfready filled with information, if not append.
        If it is filled with similar values, raise an error unless self.overwrite == True.
        """
        
        log = pd.DataFrame.from_dict(piece.log)
        events = list(log["Message"].unique())

        for event in events:
            if "start" in event or "stop" in event:
                event = event.replace(" start", "")
                event = event.replace(" stop", "")

                if event not in list(existing_df["EventName"]):
                    existing_df = existing_df.append({"EventID": str(uuid.uuid1()), "EventName": event}, ignore_index=True)

        return existing_df

    
    def get_equipment_log(self):
        """
        Create a dataframe from all equipment logs
        """

        object_dict = {"SimulationID": [], "ObjectID": [], "EventID": [], "LocationID": [], "EventStart": [], "EventStop": []}

        try:
            unique_df = pd.read_csv(self.location + "equipment_log.csv")
        except FileNotFoundError:
            unique_df = pd.DataFrame.from_dict(object_dict)

        for piece in self.equipment:
            object_log = pd.DataFrame.from_dict(piece.log)

            for i, message in enumerate(object_log["Message"]):
                for j, event in enumerate(self.unique_events["EventName"]):

                    if message == event + " start":
                        object_dict["SimulationID"].append(self.id)
                        object_dict["ObjectID"].append(piece.id)
                        object_dict["EventID"].append(self.unique_events["EventID"][j])
                        object_dict["EventStart"].append(object_log["Timestamp"][i])

                        x, y = object_log["Geometry"][i].x, object_log["Geometry"][i].y

                        for k, LocationID in enumerate(self.unique_locations["LocationID"]):
                            if x == self.unique_locations["Longitude"][k] and y == self.unique_locations["Latitude"][k]:
                                object_dict["LocationID"].append(LocationID)
                    
                    elif message == event + " stop":
                        object_dict["EventStop"].append(object_log["Timestamp"][i])

        # Create durations column
        object_df = pd.DataFrame.from_dict(object_dict)
        durations = (object_df["EventStop"] - object_df["EventStart"])
        durations_days = []
        
        for event in durations:
            durations_days.append(event.total_seconds() / 3600 / 24)

        object_df["EventDuration"] = durations_days

        # Check if combination of simulation ID and object ID already exists
        if len(unique_df["SimulationID"]) == 0:
            unique_df = object_df
            
        elif not (unique_df["SimulationID"] == self.id).any():
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        elif self.overwrite == True:
            drop_rows = []

            for i, row in enumerate(unique_df["SimulationID"] == self.id):
                if row == True:
                    drop_rows.append(i)
            
            unique_df = unique_df.drop(drop_rows, axis = 0)
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")

        self.equipment_log = unique_df


    def get_spill(self):
        """
        Obtain a log of all dreding spill
        """
        
        object_dict = {"SimulationID": [], "ObjectID": [], "EventID": [], "LocationID": [], "SpillStart": [], "SpillStop": [], "SpillDuration": [], "Spill": []}

        try:
            unique_df = pd.read_csv(self.location + "dredging_spill.csv")
        except FileNotFoundError:
            unique_df = pd.DataFrame.from_dict(object_dict)

        for piece in self.equipment:
            object_log = pd.DataFrame.from_dict(piece.log)

            for i, message in enumerate(object_log["Message"]):
                if message == "fines released":
                    loop_list = list(object_log["Message"][0:i])
                    for j, event_message in enumerate(loop_list[::-1]):
                        if "start" in event_message:
                            event_start_time = object_log["Timestamp"][i - j - 1]
                            event_start_msg = event_message.replace(" start", "")
                            break
                    
                    loop_list = list(object_log["Message"][i::])
                    for j, event_message in enumerate(loop_list):
                        if "stop" in event_message:
                            event_stop_time = object_log["Timestamp"][i + j]
                            event_stop_msg = event_message.replace(" stop", "")
                            break

                    assert event_start_msg == event_stop_msg

                    for j, event in enumerate(self.unique_events["EventName"]):
                        if event_start_msg == event:
                            object_dict["SimulationID"].append(self.id)
                            object_dict["ObjectID"].append(piece.id)
                            object_dict["EventID"].append(self.unique_events["EventID"][j])
                            object_dict["SpillStart"].append(event_start_time)
                            object_dict["SpillStop"].append(event_stop_time)
                            object_dict["SpillDuration"].append((event_stop_time - event_start_time).total_seconds() / 3600 / 24)
                            object_dict["Spill"].append(object_log["Value"][i])

                            x, y = object_log["Geometry"][i].x, object_log["Geometry"][i].y

                            for k, LocationID in enumerate(self.unique_locations["LocationID"]):
                                if x == self.unique_locations["Longitude"][k] and y == self.unique_locations["Latitude"][k]:
                                    object_dict["LocationID"].append(LocationID)

        object_df = pd.DataFrame.from_dict(object_dict)

        if len(unique_df["SimulationID"]) == 0:
            unique_df = object_df
            
        elif not (unique_df["SimulationID"] == self.id).any():
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        elif self.overwrite == True:
            drop_rows = []

            for i, row in enumerate(unique_df["SimulationID"] == self.id):
                if row == True:
                    drop_rows.append(i)
            
            unique_df = unique_df.drop(drop_rows, axis = 0)
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")
            
        self.dredging_spill = unique_df

    def get_energy(self):
        """
        Obtain a log of all energy use
        """
        
        object_dict = {"SimulationID": [], "ObjectID": [], "EventID": [], "LocationID": [], "EnergyUseStart": [], "EnergyUseStop": [], "EnergyUseDuration": [], "EnergyUse": []}

        try:
            unique_df = pd.read_csv(self.location + "energy_use.csv")
        except FileNotFoundError:
            unique_df = pd.DataFrame.from_dict(object_dict)

        for piece in self.equipment:
            object_log = pd.DataFrame.from_dict(piece.log)

            for i, message in enumerate(object_log["Message"]):
                if "Energy use" in message:
                    loop_list = list(object_log["Message"][0:i])
                    for j, event_message in enumerate(loop_list[::-1]):
                        if "start" in event_message:
                            event_start_time = object_log["Timestamp"][i - j - 1]
                            event_start_msg = event_message.replace(" start", "")
                            break
                    
                    loop_list = list(object_log["Message"][i::])
                    for j, event_message in enumerate(loop_list):
                        if "stop" in event_message:
                            event_stop_time = object_log["Timestamp"][i + j]
                            event_stop_msg = event_message.replace(" stop", "")
                            break

                    assert event_start_msg == event_stop_msg
                    
                    for j, event in enumerate(self.unique_events["EventName"]):
                        if event_start_msg == event:
                            object_dict["SimulationID"].append(self.id)
                            object_dict["ObjectID"].append(piece.id)
                            object_dict["EventID"].append(self.unique_events["EventID"][j])
                            object_dict["EnergyUseStart"].append(event_start_time)
                            object_dict["EnergyUseStop"].append(event_stop_time)
                            object_dict["EnergyUseDuration"].append((event_stop_time - event_start_time).total_seconds() / 3600 / 24)
                            object_dict["EnergyUse"].append(object_log["Value"][i])

                            x, y = object_log["Geometry"][i].x, object_log["Geometry"][i].y

                            for k, LocationID in enumerate(self.unique_locations["LocationID"]):
                                if x == self.unique_locations["Longitude"][k] and y == self.unique_locations["Latitude"][k]:
                                    object_dict["LocationID"].append(LocationID)

        object_df = pd.DataFrame.from_dict(object_dict)

        if len(unique_df["SimulationID"]) == 0:
            unique_df = object_df
            
        elif not (unique_df["SimulationID"] == self.id).any():
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        elif self.overwrite == True:
            drop_rows = []

            for i, row in enumerate(unique_df["SimulationID"] == self.id):
                if row == True:
                    drop_rows.append(i)
            
            unique_df = unique_df.drop(drop_rows, axis = 0)
            unique_df = pd.concat([unique_df, object_df], ignore_index = True)
        
        else:
            raise KeyError("Simulation ID or simulation name already exist. " + 
                           "If you wish to overwrite the existing data, set overwrite to True")
            
        self.energy_use = unique_df