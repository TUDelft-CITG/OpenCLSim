import numpy as np
import matplotlib.pyplot as plt
import time
import networkx as nx
from scipy.interpolate import griddata
import pickle
import main

class Has_grid_flow:
    def __init__(self,Data,*args,**kwargs):
        super().__init__(Data,*args,**kwargs)
        Xg, Yg = np.mgrid[0:Data.N, 0:Data.M]
        self.Xg = Xg * Data.dx + Data.x_start - Data.L * 0.1
        self.Yg = Yg * Data.dy + Data.y_start - Data.B * 0.1
        
        Xf_temp = Data.Xf.reshape(Data.Xf.size)
        Yf_temp = Data.Yf.reshape(Data.Yf.size)
        
        u_temp = Data.flow_u_input.reshape(Data.flow_u_input.size)
        v_temp = Data.flow_v_input.reshape(Data.flow_v_input.size)
        
        points = []
        
        for i in range(len(Xf_temp)):
            points.append((Xf_temp[i], Yf_temp[i]))
        
        self.flow_u = griddata(points, u_temp, (self.Xg, self.Yg), method='cubic')
        self.flow_v = griddata(points, v_temp, (self.Xg, self.Yg), method='cubic')

class Has_grid_flow2:
    def __init__(self,Data,*args,**kwargs):
        super().__init__()
        Xg, Yg = np.mgrid[0:Data.N, 0:Data.M]
        self.Xg = Xg * Data.L/Data.N
        self.Yg = Yg * Data.B/Data.M
        
        Xf_temp = Data.Xf.reshape(Data.Nf ** 2)
        Yf_temp = Data.Yf.reshape(Data.Nf ** 2)
        
        u_temp = Data.flow_u_input.reshape(Data.Nf ** 2)
        v_temp = Data.flow_v_input.reshape(Data.Nf ** 2)
        
        points = []
        
        for i in range(len(Xf_temp)):
            points.append((Xf_temp[i], Yf_temp[i]))
        
        self.flow_u = griddata(points, u_temp, (self.Xg, self.Yg), method='cubic')
        self.flow_v = griddata(points, v_temp, (self.Xg, self.Yg), method='cubic')

class Has_grid_node_dir:
    def __init__(self, Data, *args,**kwargs):
        super().__init__(Data, *args, **kwargs)
        
        self.n_start = Data.n_start
        self.m_start = Data.m_start
        self.n_target = Data.n_target
        self.m_target = Data.m_target
        
        self.G = nx.DiGraph()
        nodes = []
        for i in range(Data.N):
            for j in range(Data.M):
                nodes.append((i,j))
        self.G.add_nodes_from(nodes)

class Has_edges_load:
    def __init__(self,Data, name_textfile ,*args,**kwargs):
        super().__init__()
        with open(name_textfile, "rb") as fp:   # Unpickling
            self.edges = pickle.load(fp)

class Has_edges_create_order3_NE:
    def __init__(self, Data, *args,**kwargs):
        super().__init__()
        class_flow = Has_grid_flow2(Data)
        edges = []
        dist_x = np.array([0,1,1,1,1,2,2,3,3])
        dist_y = np.array([1,3,2,1,0,3,1,2,1]) 
        for i in range(Data.N-3):
            for j in range(Data.M-3):
                for ii in range(len(dist_x)):
                    weight = Data.weight((i,j),((i+dist_x[ii]),(j+dist_y[ii])), Data, class_flow.flow_u, class_flow.flow_v)
                    e = ((i,j),((i+dist_x[ii]),(j+dist_y[ii])), weight)
                    edges.append(e)
        self.edges = edges

class Has_edges_create_order4_NE:
    def __init__(self, Data, *args,**kwargs):
        super().__init__()
        class_flow = Has_grid_flow2(Data)
        edges = [] 
        for i in range(Data.N-4):
            for j in range(Data.M-4):
                dist_x = np.array([0,1,1,1,1,1,2,2,3,3,3,4,4])
                dist_y = np.array([1,4,3,2,1,0,3,1,4,2,1,3,1])
                for ii in range(len(dist_x)):
                    weight = Data.weight((i,j),((i+dist_x[ii]),(j+dist_y[ii])), Data, class_flow.flow_u, class_flow.flow_v)
                    e = ((i,j),((i+dist_x[ii]),(j+dist_y[ii])), weight)
                    edges.append(e)
        self.edges = edges              

class Has_edges_create_order2_alldir:
    def __init__(self, Data, *args,**kwargs):
        super().__init__()
        class_flow = Has_grid_flow2(Data)
        edges = []
        dist_x = np.array([0,1,1,1,1,2,2,0,1,1,1,1,2,2,-0,-1,-1,-1,-1,-2,-2,-0,-1,-1,-1,-1,-2,-2])
        dist_y = np.array([1,3,2,1,0,3,1,-1,-3,-2,-1,-0,-3,-1,1,3,2,1,0,3,1,-1,-3,-2,-1,-0,-3,-1,]) 
        for i in range(Data.N-2):
            for j in range(Data.M-2):
                for ii in range(len(dist_x)):
                    weight = Data.weight((i,j),((i+dist_x[ii]),(j+dist_y[ii])), Data, class_flow.flow_u, class_flow.flow_v)
                    e = ((i,j),((i+dist_x[ii]),(j+dist_y[ii])), weight)
                    edges.append(e)
        self.edges = edges

class Has_edges_create_order3_alldir:
    def __init__(self, Data, *args,**kwargs):
        super().__init__()
        class_flow = Has_grid_flow2(Data)
        edges = []
        dist_x = np.array([0,1,1,1,1,2,2,3,3,0,1,1,1,1,2,2,3,3,-0,-1,-1,-1,-1,-2,-2,-3,-3,-0,-1,-1,-1,-1,-2,-2,-3,-3])
        dist_y = np.array([1,3,2,1,0,3,1,2,1,-1,-3,-2,-1,-0,-3,1,2,1,1,3,2,1,0,3,-1,-2,-1,-1,-3,-2,-1,-0,-3,-1,-2,-1])
        for i in range(Data.N-3):
            for j in range(Data.M-3):
                for ii in range(len(dist_x)):
                    weight = Data.weight((i,j),((i+dist_x[ii]),(j+dist_y[ii])), Data, class_flow.flow_u, class_flow.flow_v)
                    e = ((i,j),((i+dist_x[ii]),(j+dist_y[ii])), weight)
                    edges.append(e)
        self.edges = edges

class Has_edges_create_order4_alldir:
    def __init__(self, Data, *args,**kwargs):
        super().__init__()
        class_flow = Has_grid_flow2(Data)
        edges = []
        dist_x = np.array([0,1,1,1,1,1,2,2,3,3,3,4,4,0,1,1,1,1,1,2,2,3,3,3,4,4,-0,-1,-1,-1,-1,-1,-2,-2,-3,-3,-3,-4,-4,-0,-1,-1,-1,-1,-1,-2,-2,-3,-3,-3,-4,-4])
        dist_y = np.array([1,4,3,2,1,0,3,1,4,2,1,3,1,-1,-4,-3,-2,-1,-0,-3,-1,-4,-2,-1,-3,-1,1,4,3,2,1,0,3,1,4,2,1,3,1,-1,-4,-3,-2,-1,-0,-3,-1,-4,-2,-1,-3,-1])
        for i in range(Data.N-4):
            for j in range(Data.M-4):
                for ii in range(len(dist_x)):
                    weight = Data.weight((i,j),((i+dist_x[ii]),(j+dist_y[ii])), Data, class_flow.flow_u, class_flow.flow_v)
                    e = ((i,j),((i+dist_x[ii]),(j+dist_y[ii])), weight)
                    edges.append(e)
        self.edges = edges