# package(s) related to time, space and id
import datetime, time
import platform

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy

# spatial libraries 
import shapely.geometry
from simplekml import Kml, Style

# digital twin package
import digital_twin.core as core
import digital_twin.model as model
import digital_twin.plot as plot

# Additional import to save the initialization of the simulation
import digital_twin.savesim as savesim
import halem
import pickle
import networkx as nx
import numpy as np

def test_halem_single_path():
    T0 = '16/04/2019 01:00:00'
    d = datetime.datetime.strptime(T0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()

    simulation_start = datetime.datetime.fromtimestamp(t0)

    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    Site = type('Site', (core.Identifiable, # Give it a name
                         core.Log,          # Allow logging of all discrete events
                         core.Locatable,    # Add coordinates to extract distance information and visualize
                         core.HasContainer, # Add information on the material available at the site
                         core.HasResource), # Add information on serving equipment
                {})   

    location_from_site = shapely.geometry.Point(4.788699, 52.970919)  # lon, lat

    data_from_site = {"env": my_env,                                # The simpy environment defined in the first cel
                      "name": "Winlocatie",                         # The name of the site
                      "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5b", # For logging purposes
                      "geometry": location_from_site,               # The coordinates of the project site
                      "capacity": 5_000,                          # The capacity of the site
                      "level": 5_000}   

    location_to_site = shapely.geometry.Point(4.541166, 53.093619)     # lon, lat

    data_to_site = {"env": my_env,                                # The simpy environment defined in the first cel
                    "name": "Dumplocatie",                        # The name of the site
                    "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5b", # For logging purposes
                    "geometry": location_to_site,                 # The coordinates of the project site
                    "capacity": 5_000,                          # The capacity of the site
                    "level": 0}     

    from_site = Site(**data_from_site)
    to_site   = Site(**data_to_site)

    TransportProcessingResource = type('TransportProcessingResource', 
                                       (core.Identifiable,              # Give it a name
                                        core.Log,                       # Allow logging of all discrete events
                                        core.ContainerDependentMovable, # A moving container, so capacity and location
                                        core.Processor,                 # Allow for loading and unloading
                                        core.HasResource,               # Add information on serving equipment
                                        core.HasCosts,
                                        ),                 # Initialize spill terms
                                       {})

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    def compute_loading(rate):
        return lambda current_level, desired_level: (desired_level - current_level) / rate

    def compute_unloading(rate):
        return lambda current_level, desired_level: (current_level - desired_level) / rate

    data_hopper = {"env": my_env,                                       # The simpy environment 
                   "name": "Hopper 01",                                 # Name
                   "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",        # For logging purposes
                   "geometry": location_from_site,                      # It starts at the "from site"
                   "loading_func": compute_loading(1.5),                # Loading rate
                   "unloading_func": compute_unloading(1.5),            # Unloading rate
                   "capacity": 5_000,                                   # Capacity of the hopper - "Beunvolume"
                   "compute_v": compute_v_provider(7, 5),             # Variable speed 
                   "weekrate": 700_000}

    hopper = TransportProcessingResource(**data_hopper)

    activity = model.Activity(env = my_env,           # The simpy environment defined in the first cel
                              name = "Soil movement", # We are moving soil
                              ID = "6dbbbdf7-4589-11e9-bf3b-b469212bff5b", # For logging purposes
                              origin = from_site,     # We originate from the from_site
                              destination = to_site,  # And therefore travel to the to_site
                              loader = hopper,        # The benefit of a TSHD, all steps can be done
                              mover = hopper,         # The benefit of a TSHD, all steps can be done
                              unloader = hopper,      # The benefit of a TSHD, all steps can be done
                              start_event = None,     # We can start right away
                              stop_event = None)      # We stop once there is nothing more to move

    name_textfile_load = 'tests/Roadmap/General_waddensea_dt=3h'

    with open(name_textfile_load, 'rb') as input:
        Roadmap = pickle.load(input)\

    my_env.Roadmap = Roadmap
    my_env.run()

    path = []
    for point in hopper.log['Geometry']:
        x = point.x
        y = point.y
        path.append((x,y))
    path = np.array(path[6:-6])


    time_path = []

    for t in hopper.log['Timestamp'][6:-6]:
        time_path.append(t.timestamp())

    time_path = np.array(time_path)

    start_loc = (location_from_site.x,location_from_site.y)
    stop_loc = (location_to_site.x,location_to_site.y)

    T0 = datetime.datetime.fromtimestamp(time_path[0]).strftime("%d/%m/%Y %H:%M:%S")
    path_calc, time_path__calc, _ = halem.HALEM_time(start_loc, stop_loc, T0, 7, Roadmap)

    np.testing.assert_array_equal(path_calc[:-2], path)
    
def test_halem_not_twice_the_same():
    T0 = '16/04/2019 01:00:00'
    d = datetime.datetime.strptime(T0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()

    simulation_start = datetime.datetime.fromtimestamp(t0)

    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    Site = type('Site', (core.Identifiable, # Give it a name
                         core.Log,          # Allow logging of all discrete events
                         core.Locatable,    # Add coordinates to extract distance information and visualize
                         core.HasContainer, # Add information on the material available at the site
                         core.HasResource), # Add information on serving equipment
                {})   

    location_from_site = shapely.geometry.Point(4.788699, 52.970919)  # lon, lat

    data_from_site = {"env": my_env,                                # The simpy environment defined in the first cel
                      "name": "Winlocatie",                         # The name of the site
                      "ID": "6dbbbdf4-4589-11e9-a501-b469212bff5b", # For logging purposes
                      "geometry": location_from_site,               # The coordinates of the project site
                      "capacity": 20_000,                          # The capacity of the site
                      "level": 20_000}   

    location_to_site = shapely.geometry.Point(4.541166, 53.093619)     # lon, lat

    data_to_site = {"env": my_env,                                # The simpy environment defined in the first cel
                    "name": "Dumplocatie",                        # The name of the site
                    "ID": "6dbbbdf5-4589-11e9-82b2-b469212bff5b", # For logging purposes
                    "geometry": location_to_site,                 # The coordinates of the project site
                    "capacity": 20_000,                          # The capacity of the site
                    "level": 0}     

    from_site = Site(**data_from_site)
    to_site   = Site(**data_to_site)

    TransportProcessingResource = type('TransportProcessingResource', 
                                       (core.Identifiable,              # Give it a name
                                        core.Log,                       # Allow logging of all discrete events
                                        core.ContainerDependentMovable, # A moving container, so capacity and location
                                        core.Processor,                 # Allow for loading and unloading
                                        core.HasResource,               # Add information on serving equipment
                                        core.HasCosts,
                                        ),                 # Initialize spill terms
                                       {})

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    def compute_loading(rate):
        return lambda current_level, desired_level: (desired_level - current_level) / rate

    def compute_unloading(rate):
        return lambda current_level, desired_level: (current_level - desired_level) / rate

    data_hopper = {"env": my_env,                                       # The simpy environment 
                   "name": "Hopper 01",                                 # Name
                   "ID": "6dbbbdf6-4589-11e9-95a2-b469212bff5b",        # For logging purposes
                   "geometry": location_from_site,                      # It starts at the "from site"
                   "loading_func": compute_loading(1.5),                # Loading rate
                   "unloading_func": compute_unloading(1.5),            # Unloading rate
                   "capacity": 5_000,                                   # Capacity of the hopper - "Beunvolume"
                   "compute_v": compute_v_provider(7, 5),             # Variable speed 
                   "weekrate": 700_000}

    hopper = TransportProcessingResource(**data_hopper)

    activity = model.Activity(env = my_env,           # The simpy environment defined in the first cel
                              name = "Soil movement", # We are moving soil
                              ID = "6dbbbdf7-4589-11e9-bf3b-b469212bff5b", # For logging purposes
                              origin = from_site,     # We originate from the from_site
                              destination = to_site,  # And therefore travel to the to_site
                              loader = hopper,        # The benefit of a TSHD, all steps can be done
                              mover = hopper,         # The benefit of a TSHD, all steps can be done
                              unloader = hopper,      # The benefit of a TSHD, all steps can be done
                              start_event = None,     # We can start right away
                              stop_event = None)      # We stop once there is nothing more to move

    name_textfile_load = 'tests/Roadmap/General_waddensea_dt=3h'

    with open(name_textfile_load, 'rb') as input:
        Roadmap = pickle.load(input)\

    my_env.Roadmap = Roadmap
    my_env.run()

    path = []
    for point in hopper.log['Geometry']:
        x = point.x
        y = point.y
        path.append((x,y))
    path = np.array(path)

    M = np.array(hopper.log['Message'])
    sailing_full_idx = np.argwhere(M == 'sailing filled start')
    sailing_empt_idx = np.argwhere(M == 'sailing empty start')

    full = []
    empt = []

    for i in range(len(sailing_empt_idx)):
        full.append(path[sailing_full_idx[i][0]+2:sailing_empt_idx[i][0] - 7])
        empt.append(path[sailing_empt_idx[i][0]+2:sailing_full_idx[i+1][0] - 7])

    for QQ in [[0,1],[0,2],[1,2]]:
        np.testing.assert_raises(AssertionError, np.testing.assert_array_equal, full[QQ[0]], full[QQ[1]])
        np.testing.assert_raises(AssertionError, np.testing.assert_array_equal, empt[QQ[0]], empt[QQ[1]])
        

def test_halem_hopper_on_route():       
    t0 = '16/04/2019 01:00:00'
    d = datetime.datetime.strptime(t0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()

    simulation_start = datetime.datetime.fromtimestamp(t0)

    my_env = simpy.Environment(initial_time = time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    def connect_sites_with_path(data_from_site, data_to_site, data_node, path):
        Nodes = []
        Edges = []
        Site = type('Site', (core.Identifiable, # Give it a name
                 core.Log,          # Allow logging of all discrete events
                 core.Locatable,    # Add coordinates to extract distance information and visualize
                 core.HasContainer, # Add information on the material available at the site
                 core.HasResource), # Add information on serving equipment
        {})                         # The dictionary is empty because the site type is generic

        Node = type('Node', (core.Identifiable, # Give it a name
                 core.Log,          # Allow logging of all discrete events
                 core.Locatable),   # Add coordinates to extract distance information and visualize
        {})                         # The dictionary is empty because the site type is generic

        for i, j in enumerate(path):
            if i == 0:
                data_from_site["geometry"]=shapely.geometry.Point(path[i][0], path[i][1])
                Nodes.append(Site(**data_from_site))

            elif i == len(path) - 1:
                data_to_site["geometry"]=shapely.geometry.Point(path[i][0], path[i][1])
                Nodes.append(Site(**data_to_site))
                Edges.append([Nodes[i-1], Nodes[i]])

            else:
                data_node["geometry"]=shapely.geometry.Point(path[i][0], path[i][1])
                data_node["name"]='node-' + str(i)
                Nodes.append(Node(**data_node))
                Edges.append([Nodes[i-1], Nodes[i]])

        return Nodes, Edges

    data_from_site = {"env": my_env,                  # The simpy environment defined in the first cel
                      "name": "Winlocatie",           # The name of the site
                      "geometry": [],                 # The coordinates of the project site
                      "capacity": 5_000,            # The capacity of the site
                      "level": 5_000}               # The actual volume of the site

    data_node = {"env": my_env,                      # The simpy environment defined in the first cel
                     "name": "Intermediate site",     # The name of the site
                     "geometry": []}                  # The coordinates of the project site

    data_to_site = {"env": my_env,                    # The simpy environment defined in the first cel
                    "name": "Dumplocatie",            # The name of the site
                    "geometry": [],                   # The coordinates of the project site
                    "capacity": 5_000,              # The capacity of the site
                    "level": 0}     

    path = [[4.788699, 52.970919],
            [4.568443, 52.922208],
            [4.541166, 53.093619],
           ]

    Nodes, Edges = connect_sites_with_path(data_from_site, data_to_site, data_node, path)

    FG = nx.Graph()

    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry = node.geometry)


    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight = 1)

    TransportProcessingResource = type('TransportProcessingResource', 
                                       (core.Identifiable,              # Give it a name
                                        core.Log,                       # Allow logging of all discrete events
                                        core.ContainerDependentMovable, # A moving container, so capacity and location
                                        core.Processor,                 # Allow for loading and unloading
                                        core.HasResource,               # Add information on serving equipment
                                        core.Routeable),                 # Initialize spill terms
                                       {})

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    def compute_loading(rate):
        return lambda current_level, desired_level: (desired_level - current_level) / rate

    def compute_unloading(rate):
        return lambda current_level, desired_level: (current_level - desired_level) / rate

    route = []

    # TSHD variables
    data_hopper = {"env": my_env,                                       # The simpy environment 
                   "name": "Hopper 01",                                 # Name
                   "geometry": Nodes[0].geometry,                      # It starts at the "from site"
                   "loading_func": compute_loading(1.5),                # Loading rate
                   "unloading_func": compute_unloading(1.5),            # Unloading rate
                   "capacity": 5_000,                                   # Capacity of the hopper - "Beunvolume"
                   "compute_v": compute_v_provider(7, 5),             # Variable speed
                   "route": route}     

    hopper = TransportProcessingResource(**data_hopper)

    activity = model.Activity(env = my_env,             # The simpy environment defined in the first cel
                              name = "Soil movement",   # We are moving soil
                              origin = Nodes[0],        # We originate from the from_site
                              destination = Nodes[-1],  # And therefore travel to the to_site
                              loader = hopper,          # The benefit of a TSHD, all steps can be done
                              mover = hopper,           # The benefit of a TSHD, all steps can be done
                              unloader = hopper,        # The benefit of a TSHD, all steps can be done
                              start_event = None,       # We can start right away
                              stop_event = None)        # We stop once there is nothing more to move

    name_textfile_load = 'tests/Roadmap/General_waddensea_dt=3h'

    with open(name_textfile_load, 'rb') as input:
        Roadmap = pickle.load(input)\

    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()


    path = []
    for point in hopper.log['Geometry']:
        x = point.x
        y = point.y
        path.append((x,y))
    path = np.array(path[6:-6])

    assert [4.568443, 52.922208] in path