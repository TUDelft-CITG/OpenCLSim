import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import pickle
import main

class Path_Dijkstra:
    def __init__(self, Graph, Data, *args,**kwargs):
        super().__init__(Graph,*args,**kwargs)
        self.route = np.array(nx.dijkstra_path(Graph.G, (Graph.n_start,Graph.m_start), (Graph.n_target,Graph.m_target)))
        self.route[:,0] = self.route[:,0]* Data.dx + Data.x_start - Data.L * 0.1
        self.route[:,1] = self.route[:,1]* Data.dy + Data.y_start - Data.B * 0.1

class Path_length_Dijkstra:
    def __init__(self, Graph,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.score = nx.dijkstra_path_length(Graph.G, (Graph.n_start,Graph.m_start), (Graph.n_target,Graph.m_target))

class Path_Astar:
    def __init__(self, Graph, Data, *args,**kwargs):
        super().__init__(Graph,Data,*args,**kwargs)
        def CF(a,b):
            weight = Data.weight(a,b,Data = Data)
            return weight
        self.route = np.array(nx.astar_path(Graph.G, (Graph.n_start,Graph.m_start), (Graph.n_target,Graph.m_target), CF))
        self.route[:,0] = self.route[:,0]*Data.dx
        self.route[:,1] = self.route[:,1]*Data.dy

class Path_length_Astar:
    def __init__(self, Graph, Data,*args,**kwargs):
        super().__init__(*args,**kwargs)
        def CF(a,b):
            weight = Data.weight(a,b,Data = Data)
            return weight
        self.score = nx.astar_path_length(Graph.G, (Graph.n_start,Graph.m_start), (Graph.n_target,Graph.m_target), CF)


class Save_edges_to_text:
    def __init__(self, name_textfile_save, Graph ,*args,**kwargs):
        super().__init__()
        with open(name_textfile_save, "wb") as fp:   #Pickling
            pickle.dump(Graph.edges, fp)