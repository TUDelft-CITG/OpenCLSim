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
import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot

# Additional import to save the initialization of the simulation
import openclsim.savesim as savesim
import halem
import pickle
import networkx as nx
import numpy as np
from scipy.spatial import Delaunay


def test_halem_single_path():
    name_textfile_load = "tests/Roadmap/General_waddensea_dt=3h"
    with open(name_textfile_load, "rb") as input:
        Roadmap = pickle.load(input)
    t0 = "17/04/2019 01:00:00"
    start = (4.788699, 52.970919)
    stop = (4.541166, 53.093619)
    d = datetime.datetime.strptime(t0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()
    simulation_start = datetime.datetime.fromtimestamp(t0)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    def connect_sites_with_path(data_from_site, data_to_site, data_node, path):
        Nodes = []
        Edges = []
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

        Node = type(
            "Node",
            (
                core.Identifiable,  # Give it a name
                core.Log,  # Allow logging of all discrete events
                core.Locatable,
            ),  # Add coordinates to extract distance information and visualize
            {},
        )  # The dictionary is empty because the site type is generic

        for i, j in enumerate(path):
            if i == 0:
                data_from_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_from_site))

            elif i == len(path) - 1:
                data_to_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_to_site))
                Edges.append([Nodes[i - 1], Nodes[i]])

            else:
                data_node["geometry"] = shapely.geometry.Point(path[i][0], path[i][1])
                data_node["name"] = "node-" + str(i)
                Nodes.append(Node(**data_node))
                Edges.append([Nodes[i - 1], Nodes[i]])

        return Nodes, Edges

    data_from_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Winlocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 5_000,
    }  # The actual volume of the site
    data_node = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Intermediate site",  # The name of the site
        "geometry": [],
    }  # The coordinates of the project site
    data_to_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Dumplocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 0,
    }  # The actual volume of the site (empty of course)
    path = [start, stop]
    Nodes, Edges = connect_sites_with_path(
        data_from_site, data_to_site, data_node, path
    )
    FG = nx.Graph()
    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry=node.geometry)
    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight=1)
    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.Routeable,
        ),  # Initialize spill terms
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    route = []
    data_hopper = {
        "env": my_env,  # The simpy environment
        "name": "Hopper 01",  # Name
        "geometry": Nodes[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity of the hopper - "Beunvolume"
        "compute_v": compute_v_provider(7, 5),  # Variable speed
        "route": route,
        "optimize_route": True,  # Optimize the Route
        "optimization_type": "time",  # Optimize for the fastest path
    }
    hopper = TransportProcessingResource(**data_hopper)
    activity = model.Activity(
        env=my_env,  # The simpy environment defined in the first cel
        name="Soil movement",  # We are moving soil
        origin=Nodes[0],  # We originate from the from_site
        destination=Nodes[-1],  # And therefore travel to the to_site
        loader=hopper,  # The benefit of a TSHD, all steps can be done
        mover=hopper,  # The benefit of a TSHD, all steps can be done
        unloader=hopper,  # The benefit of a TSHD, all steps can be done
        start_event=None,  # We can start right away
        stop_event=None,
    )  # We stop once there is nothing more to move
    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()
    path_MVK = []
    for g in hopper.log["Geometry"]:
        path_MVK.append([g.x, g.y])

    path_MVK = np.array(path_MVK)
    path_MVK = path_MVK[3:-4, :]
    vmax = 7
    path_halem, time_halem, _ = halem.HALEM_time(
        start, stop, "17/04/2019 1:58:18", vmax, Roadmap
    )

    np.testing.assert_array_equal(path_halem[:-1, :], path_MVK[:-1, :])


def test_halem_not_twice_the_same():
    name_textfile_load = "tests/Roadmap/General_waddensea_dt=3h"

    with open(name_textfile_load, "rb") as input:
        Roadmap = pickle.load(input)
    t0 = Roadmap.t[1]

    simulation_start = datetime.datetime.fromtimestamp(t0)

    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    def connect_sites_with_path(data_from_site, data_to_site, data_node, path):
        Nodes = []
        Edges = []
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

        Node = type(
            "Node",
            (
                core.Identifiable,  # Give it a name
                core.Log,  # Allow logging of all discrete events
                core.Locatable,
            ),  # Add coordinates to extract distance information and visualize
            {},
        )  # The dictionary is empty because the site type is generic

        for i, j in enumerate(path):
            if i == 0:
                data_from_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_from_site))

            elif i == len(path) - 1:
                data_to_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_to_site))
                Edges.append([Nodes[i - 1], Nodes[i]])

            else:
                data_node["geometry"] = shapely.geometry.Point(path[i][0], path[i][1])
                data_node["name"] = "node-" + str(i)
                Nodes.append(Node(**data_node))
                Edges.append([Nodes[i - 1], Nodes[i]])

        return Nodes, Edges

    data_from_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Winlocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 15_000,  # The capacity of the site
        "level": 15_000,
    }  # The actual volume of the site

    data_node = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Intermediate site",  # The name of the site
        "geometry": [],
    }  # The coordinates of the project site

    data_to_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Dumplocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 15_000,  # The capacity of the site
        "level": 0,
    }

    path = [[4.788699, 52.970919], [4.541166, 53.093619]]

    Nodes, Edges = connect_sites_with_path(
        data_from_site, data_to_site, data_node, path
    )

    FG = nx.Graph()

    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry=node.geometry)

    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight=1)

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.Routeable,
        ),  # Initialize spill terms
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    route = []

    # TSHD variables
    data_hopper = {
        "env": my_env,  # The simpy environment
        "name": "Hopper 01",  # Name
        "geometry": Nodes[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity of the hopper - "Beunvolume"
        "compute_v": compute_v_provider(7, 5),  # Variable speed
        "route": route,
        "optimize_route": True,  # Optimize the Route
        "optimization_type": "time",  # Optimize for the fastest path
    }

    hopper = TransportProcessingResource(**data_hopper)

    activity = model.Activity(
        env=my_env,  # The simpy environment defined in the first cel
        name="Soil movement",  # We are moving soil
        origin=Nodes[0],  # We originate from the from_site
        destination=Nodes[-1],  # And therefore travel to the to_site
        loader=hopper,  # The benefit of a TSHD, all steps can be done
        mover=hopper,  # The benefit of a TSHD, all steps can be done
        unloader=hopper,  # The benefit of a TSHD, all steps can be done
        start_event=None,  # We can start right away
        stop_event=None,
    )  # We stop once there is nothing more to move

    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()

    path = []
    for point in hopper.log["Geometry"]:
        x = point.x
        y = point.y
        path.append((x, y))
    path = np.array(path)

    M = np.array(hopper.log["Message"])
    sailing_full_idx = np.argwhere(M == "sailing filled start")
    sailing_empt_idx = np.argwhere(M == "sailing empty start")

    full = []
    empt = []

    for i in range(len(sailing_empt_idx)):
        full.append(path[sailing_full_idx[i][0] + 2 : sailing_empt_idx[i][0] - 7])
        empt.append(path[sailing_empt_idx[i][0] + 2 : sailing_full_idx[i + 1][0] - 7])

    np.testing.assert_raises(
        AssertionError, np.testing.assert_array_equal, full[0], full[1]
    )
    np.testing.assert_raises(
        AssertionError, np.testing.assert_array_equal, empt[0], empt[1]
    )


def test_halem_hopper_on_route():
    t0 = "16/04/2019 01:00:00"
    d = datetime.datetime.strptime(t0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()

    simulation_start = datetime.datetime.fromtimestamp(t0)

    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    def connect_sites_with_path(data_from_site, data_to_site, data_node, path):
        Nodes = []
        Edges = []
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

        Node = type(
            "Node",
            (
                core.Identifiable,  # Give it a name
                core.Log,  # Allow logging of all discrete events
                core.Locatable,
            ),  # Add coordinates to extract distance information and visualize
            {},
        )  # The dictionary is empty because the site type is generic

        for i, j in enumerate(path):
            if i == 0:
                data_from_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_from_site))

            elif i == len(path) - 1:
                data_to_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_to_site))
                Edges.append([Nodes[i - 1], Nodes[i]])

            else:
                data_node["geometry"] = shapely.geometry.Point(path[i][0], path[i][1])
                data_node["name"] = "node-" + str(i)
                Nodes.append(Node(**data_node))
                Edges.append([Nodes[i - 1], Nodes[i]])

        return Nodes, Edges

    data_from_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Winlocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 5_000,
    }  # The actual volume of the site

    data_node = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Intermediate site",  # The name of the site
        "geometry": [],
    }  # The coordinates of the project site

    data_to_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Dumplocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 0,
    }

    path = [[4.788699, 52.970919], [4.568443, 52.922208], [4.541166, 53.093619]]

    Nodes, Edges = connect_sites_with_path(
        data_from_site, data_to_site, data_node, path
    )

    FG = nx.Graph()

    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry=node.geometry)

    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight=1)

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.Routeable,
        ),  # Initialize spill terms
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    route = []

    # TSHD variables
    data_hopper = {
        "env": my_env,  # The simpy environment
        "name": "Hopper 01",  # Name
        "geometry": Nodes[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity of the hopper - "Beunvolume"
        "compute_v": compute_v_provider(7, 5),  # Variable speed
        "route": route,
        "optimize_route": True,  # Optimize the Route
        "optimization_type": "time",  # Optimize for the fastest path
    }

    hopper = TransportProcessingResource(**data_hopper)

    activity = model.Activity(
        env=my_env,  # The simpy environment defined in the first cel
        name="Soil movement",  # We are moving soil
        origin=Nodes[0],  # We originate from the from_site
        destination=Nodes[-1],  # And therefore travel to the to_site
        loader=hopper,  # The benefit of a TSHD, all steps can be done
        mover=hopper,  # The benefit of a TSHD, all steps can be done
        unloader=hopper,  # The benefit of a TSHD, all steps can be done
        start_event=None,  # We can start right away
        stop_event=None,
    )  # We stop once there is nothing more to move

    name_textfile_load = "tests/Roadmap/General_waddensea_dt=3h"

    with open(name_textfile_load, "rb") as input:
        Roadmap = pickle.load(input)
    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()

    path = []
    for point in hopper.log["Geometry"]:
        x = point.x
        y = point.y
        path.append((x, y))
    path = np.array(path[6:-6])

    assert [4.568443, 52.922208] in path


def test_load_factor_optimiziation_with_HALEM():
    class flow_potentiaalveld:
        def __init__(self, name):
            d = datetime.datetime.strptime("23/03/2019 00:00:00", "%d/%m/%Y %H:%M:%S")
            t0 = d.timestamp()
            x = np.arange(0, 1, 0.1)
            y = np.arange(0, 1, 0.1)
            t = np.arange(t0, (t0 + 2 * 30 * 60 * 30), 30 * 60)

            y, x = np.meshgrid(y, x)
            y = y.reshape(y.size)
            x = x.reshape(y.size)

            nodes = np.zeros((len(x), 2))
            nodes[:, 0] = y
            nodes[:, 1] = x

            u = []
            v = []
            for node in nodes:
                ut = 0 * t + 2 * np.cos(np.pi * (node[0]))
                vt = 0 * t - 2 * np.cos(np.pi * (node[1]))
                u.append(ut)
                v.append(vt)

            self.v = np.transpose(np.array(v))
            self.u = np.transpose(np.array(u))
            self.WD = np.random.rand(self.u.shape[0], self.u.shape[1]) * 12 + 8
            self.t = t
            self.nodes = nodes
            self.tria = Delaunay(nodes)

    nl = (3, 2.5)
    dx_min = 0.01
    blend = 1
    vship = np.array([[8], [10], [7]])
    WD_min = np.array([7, 7, 7])
    WPVI = np.array([10000, 10000, 10000])
    ukc = 1.5
    WWL = 40
    name_textfile_flow = "maaktnietuit"
    Load_flow = flow_potentiaalveld
    number_of_neighbor_layers = 1

    loadfactors = [0, 0.99999, 1]

    Roadmap = halem.Mesh_maker.Graph_flow_model(
        name_textfile_flow,
        dx_min,
        blend,
        nl,
        number_of_neighbor_layers,
        vship,
        Load_flow,
        WD_min,
        WPVI,
        WWL=WWL,
        ukc=ukc,
    )

    def connect_sites_with_path(data_from_site, data_to_site, data_node, path):
        Nodes = []
        Edges = []
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

        Node = type(
            "Node",
            (
                core.Identifiable,  # Give it a name
                core.Log,  # Allow logging of all discrete events
                core.Locatable,
            ),  # Add coordinates to extract distance information and visualize
            {},
        )  # The dictionary is empty because the site type is generic

        for i, j in enumerate(path):
            if i == 0:
                data_from_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_from_site))

            elif i == len(path) - 1:
                data_to_site["geometry"] = shapely.geometry.Point(
                    path[i][0], path[i][1]
                )
                Nodes.append(Site(**data_to_site))
                Edges.append([Nodes[i - 1], Nodes[i]])

            else:
                data_node["geometry"] = shapely.geometry.Point(path[i][0], path[i][1])
                data_node["name"] = "node-" + str(i)
                Nodes.append(Node(**data_node))
                Edges.append([Nodes[i - 1], Nodes[i]])

        return Nodes, Edges

    t0 = "17/04/2019 01:00:00"
    start = (0.2, 0.2)
    stop = (0.8, 0.8)
    d = datetime.datetime.strptime(t0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()
    simulation_start = datetime.datetime.fromtimestamp(t0)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    data_from_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Winlocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 5_000,
    }  # The actual volume of the site
    data_node = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Intermediate site",  # The name of the site
        "geometry": [],
    }  # The coordinates of the project site
    data_to_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Dumplocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 0,
    }  # The actual volume of the site (empty of course)
    path = [start, stop]
    Nodes, Edges = connect_sites_with_path(
        data_from_site, data_to_site, data_node, path
    )
    FG = nx.Graph()
    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry=node.geometry)
    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight=1)
    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.Routeable,
        ),  # Initialize spill terms
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    route = []
    data_hopper = {
        "env": my_env,  # The simpy environment
        "name": "Hopper 01",  # Name
        "geometry": Nodes[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity of the hopper - "Beunvolume"
        "compute_v": compute_v_provider(7, 5),  # Variable speed
        "route": route,
        "optimize_route": True,  # Optimize the Route
        "optimization_type": "time",  # Optimize for the fastest path
        "loadfactors": loadfactors,
    }
    hopper = TransportProcessingResource(**data_hopper)
    activity = model.Activity(
        env=my_env,  # The simpy environment defined in the first cel
        name="Soil movement",  # We are moving soil
        origin=Nodes[0],  # We originate from the from_site
        destination=Nodes[-1],  # And therefore travel to the to_site
        loader=hopper,  # The benefit of a TSHD, all steps can be done
        mover=hopper,  # The benefit of a TSHD, all steps can be done
        unloader=hopper,  # The benefit of a TSHD, all steps can be done
        start_event=None,  # We can start right away
        stop_event=None,
    )  # We stop once there is nothing more to move
    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()

    no_opt_LF = len(
        list(set(np.array(hopper.log["Value"])[np.array(hopper.log["Value"]) > 0]))
    )

    t0 = "17/04/2019 01:00:00"
    start = (0.2, 0.2)
    stop = (0.8, 0.8)
    d = datetime.datetime.strptime(t0, "%d/%m/%Y %H:%M:%S")
    t0 = d.timestamp()
    simulation_start = datetime.datetime.fromtimestamp(t0)
    my_env = simpy.Environment(initial_time=time.mktime(simulation_start.timetuple()))
    my_env.epoch = time.mktime(simulation_start.timetuple())

    data_from_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Winlocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 5_000,
    }  # The actual volume of the site
    data_node = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Intermediate site",  # The name of the site
        "geometry": [],
    }  # The coordinates of the project site
    data_to_site = {
        "env": my_env,  # The simpy environment defined in the first cel
        "name": "Dumplocatie",  # The name of the site
        "geometry": [],  # The coordinates of the project site
        "capacity": 5_000,  # The capacity of the site
        "level": 0,
    }  # The actual volume of the site (empty of course)
    path = [start, stop]
    Nodes, Edges = connect_sites_with_path(
        data_from_site, data_to_site, data_node, path
    )
    FG = nx.Graph()
    positions = {}
    for node in Nodes:
        positions[node.name] = (node.geometry.x, node.geometry.y)
        FG.add_node(node.name, geometry=node.geometry)
    for edge in Edges:
        FG.add_edge(edge[0].name, edge[1].name, weight=1)
    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,  # Give it a name
            core.Log,  # Allow logging of all discrete events
            core.ContainerDependentMovable,  # A moving container, so capacity and location
            core.Processor,  # Allow for loading and unloading
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,  # Add information on serving equipment
            core.Routeable,
        ),  # Initialize spill terms
        {},
    )

    def compute_v_provider(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    route = []

    data_hopper = {
        "env": my_env,  # The simpy environment
        "name": "Hopper 01",  # Name
        "geometry": Nodes[0].geometry,  # It starts at the "from site"
        "loading_rate": 1.5,  # Loading rate
        "unloading_rate": 1.5,  # Unloading rate
        "capacity": 5_000,  # Capacity of the hopper - "Beunvolume"
        "compute_v": compute_v_provider(7, 5),  # Variable speed
        "route": route,
        "optimize_route": True,  # Optimize the Route
        "optimization_type": "time",  # Optimize for the fastest path
    }
    hopper = TransportProcessingResource(**data_hopper)
    activity = model.Activity(
        env=my_env,  # The simpy environment defined in the first cel
        name="Soil movement",  # We are moving soil
        origin=Nodes[0],  # We originate from the from_site
        destination=Nodes[-1],  # And therefore travel to the to_site
        loader=hopper,  # The benefit of a TSHD, all steps can be done
        mover=hopper,  # The benefit of a TSHD, all steps can be done
        unloader=hopper,  # The benefit of a TSHD, all steps can be done
        start_event=None,  # We can start right away
        stop_event=None,
    )  # We stop once there is nothing more to move
    my_env.FG = FG
    my_env.Roadmap = Roadmap
    my_env.run()

    opt_LF = len(
        list(set(np.array(hopper.log["Value"])[np.array(hopper.log["Value"]) > 0]))
    )

    assert opt_LF < no_opt_LF
