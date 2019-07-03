import halem.Mesh_maker as Mesh_maker
import halem.Functions as Functions
import halem.Calc_path as Calc_path
import halem.Flow_class as Flow_class

import pytest
import numpy as np
from scipy.spatial import Delaunay
from scipy.signal import argrelextrema
from IPython.display import clear_output

class flow_class():
    def __init__(self, name =  'maaktnietuit'):
        self.t = np.arange(0,10)
        
        x = np.arange(0,10,0.5)
        y = np.arange(10,20,0.5)
        yy, xx = np.meshgrid(y,x)
        xx = xx.reshape(xx.size)
        yy = yy.reshape(yy.size)
        self.nodes = np.zeros((len(xx),2))
        self.nodes[:,1] = xx
        self.nodes[:,0] = yy
        self.tria = Delaunay(self.nodes)
        
        self.WD = np.ones((len(self.t), len(self.nodes)))*100
        self.u = [np.sin(np.pi*self.nodes[:,1]/5)]
        self.v = [np.cos(np.pi*self.nodes[:,1]/5)]
        u = self.u
        v = self.v
        
        
        for i in range(len(self.t)-1):
            self.u = np.concatenate((self.u, u))
            self.v = np.concatenate((self.v, v))
            
class flow_class2():
    def __init__(self):
        self.t = np.arange(0,10)
        
        x = np.arange(0,10,0.5)
        y = np.arange(10,20,0.5)
        yy, xx = np.meshgrid(y,x)
        xx = xx.reshape(xx.size)
        yy = yy.reshape(yy.size)
        self.nodes = np.zeros((len(xx),2))
        self.nodes[:,1] = xx
        self.nodes[:,0] = yy
        self.tria = Delaunay(self.nodes)
        
        self.WD = np.ones((len(self.t), len(self.nodes)))*100
        self.u = [np.sin(np.pi*self.nodes[:,0]/5)]
        self.v = [np.cos(np.pi*self.nodes[:,0]/5)]
        u = self.u
        v = self.v
        
        
        for i in range(len(self.t)-1):
            self.u = np.concatenate((self.u, u))
            self.v = np.concatenate((self.v, v))
            
class flow_class3():
    def __init__(self):
        self.t = np.arange(0,10)
        
        x = np.arange(0,10,0.5)
        y = np.arange(10,20,0.5)
        yy, xx = np.meshgrid(y,x)
        xx = xx.reshape(xx.size)
        yy = yy.reshape(yy.size)
        self.nodes = np.zeros((len(xx),2))
        self.nodes[:,1] = xx
        self.nodes[:,0] = yy
        self.tria = Delaunay(self.nodes)
        
        self.WD = np.ones((len(self.t), len(self.nodes)))*100
        self.u = [np.sin(np.pi*self.nodes[:,0]/5)]
        self.v = [-np.cos(np.pi*self.nodes[:,1]/5)]
        u = self.u
        v = self.v
        
        
        for i in range(len(self.t)-1):
            self.u = np.concatenate((self.u, u))
            self.v = np.concatenate((self.v, v))


def test_Graph():
    node1 = 1
    node2 = 2
    node3 = 3
    weight = np.pi
    G = Mesh_maker.Graph()
    
    G.add_edge(node1,node2,weight)
    assert G.weights[1,2] == weight
    assert G.edges[node1] == [node2]
    assert G.edges[node2] == []
    assert G.edges[node3] == []

    G.add_edge(node1,node3,weight)
    assert G.weights[1,3] == weight
    assert G.edges[node1] == [node2, node3]
    assert G.edges[node2] == []
    assert G.edges[node3] == []

    G.add_edge(node2,node1,weight)
    assert G.weights[2,1] == weight
    assert G.edges[node1] == [node2, node3]
    assert G.edges[node2] == [node1]
    assert G.edges[node3] == []


    G.add_edge(node2,node3,weight)
    assert G.weights[2,3] == weight
    assert G.edges[node1] == [node2, node3]
    assert G.edges[node2] == [node1, node3]
    assert G.edges[node3] == []

    G.add_edge(node3,node1,weight)
    assert G.weights[3,1] == weight
    assert G.edges[node1] == [node2, node3]
    assert G.edges[node2] == [node1, node3]
    assert G.edges[node3] == [node1]

    G.add_edge(node3,node2,weight)
    assert G.weights[3,2] == weight
    assert G.edges[node1] == [node2, node3]
    assert G.edges[node2] == [node1, node3]
    assert G.edges[node3] == [node1, node2]

def test_find_neighbor():
    nodes =[(3,3),
            (2,2),(2,4),(4,2),(4,4), 
            (1,1),(1,3),(1,5),(3,1),(3,5),(5,1),(5,3),(5,5),
            (0,0),(0,2),(0,4),(0,6),(2,0),(4,0),(2,6),(4,6),(6,0),(6,2),(6,4),(6,6),
           ] 

    tria = Delaunay(nodes)
    nb = Mesh_maker.find_neighbors(0, tria)
    
    assert len(nb) == 4
    for i in range(1,5):
        assert i in nb

def test_find_neighbor2():
    nodes =[(3,3),
            (2,2),(2,4),(4,2),(4,4), 
            (1,1),(0.9,3),(1,5),(3,1),(3,5.1),(5,1),(5,3),(5,5),
            (0,0),(-.1,2),(-.1,4),(0,6),(2,0),(4,0),(2,6.1),(4,6.1),(6,0),(6,2),(6,4.1),(6,6),
           ] 
    tria = Delaunay(nodes)
    
    nb = Mesh_maker.find_neighbors2(0, tria,0)
    assert len(nb) == 0
    
    nb = Mesh_maker.find_neighbors2(0, tria,1)
    assert len(nb) == 4
    for i in range(1,5):
        assert i in nb
        
    nb = Mesh_maker.find_neighbors2(0, tria,2)
    assert len(nb) == 12
    for i in range(1,13):
        assert i in nb

    nb = Mesh_maker.find_neighbors2(0, tria,3)
    assert len(nb) == 24
    for i in range(1,25):
        assert i in nb

def test_FIFO_maker2():
    x = np.arange(0,2*np.pi,0.01)
    y = 2*np.sin(x)+x
    N1 = np.full(len(y), False)
    y = Mesh_maker.FIFO_maker2(y, N1)
    loc_min = argrelextrema(y, np.less)
    assert len(loc_min[0]) == 0
    
    x = np.arange(0,4*np.pi,0.01)
    y = 2*np.sin(x)+x
    y = Mesh_maker.FIFO_maker2(y, N1)
    loc_min = argrelextrema(y, np.less)
    assert len(loc_min[0]) == 0
    
def test_closest_node():
    nodes = np.array([(0,0),(-1,-1),(-2,2),(-2,-2),(2,2),(2,-2),(0,1)])
    node = 0
    node_list = np.arange(1,5, dtype=int)

    cn = Mesh_maker.closest_node(node,node_list, nodes)
    assert cn == 1
    
def test_Length_scale():
    flow = flow_class()
    blend = 0
    nl = (1,1)

    nodes = (flow.nodes)
    for i in range(len(flow.nodes)):
        ls = Mesh_maker.Length_scale(i, flow, blend, nl)
        assert ls == 0.5
        
    blend = 1
    nl = (1,1)
    error = 0
    for i in range(len(flow.nodes)):
        ls = Mesh_maker.Length_scale(i, flow, blend, nl)
        C = np.pi/5 * np.sin(2*np.pi*flow.nodes[i,1]/10)
        LS = 1/(1+abs(C))  
        assert abs(LS - ls) < 0.2 * LS 
        e = abs(LS - ls)/LS 
        if e > error:
            error = e
    # print(error)
    
    flow = flow_class2()
    blend = 1
    nl = (1,1)
    error = 0
    for i in range(len(flow.nodes)):
        ls = Mesh_maker.Length_scale(i, flow, blend, nl)
        C = np.pi/5 * np.cos(2*np.pi*flow.nodes[i,0]/10)
        LS = 1/(1+abs(C))  
        assert abs(LS - ls) < 0.2 * LS 
        e = abs(LS - ls)/LS 
        if e > error:
            error = e
    # print(error)
    
    flow = flow_class3()
    blend = 1
    nl = (1,1)
    error = 0
    for i in range(len(flow.nodes)):
        ls = Mesh_maker.Length_scale(i, flow, blend, nl)
        C = np.pi/5 * (np.cos(2*np.pi*flow.nodes[i,0]/10)-np.sin(2*np.pi*flow.nodes[i,1]/10))
        LS = 1/(1+abs(C))  
        assert abs(LS - ls) < 0.2
        e = abs(LS - ls)/LS 
        if e > error:
            error = e
    # print(error)
    
def test_Get_nodes():
    flow = flow_class()
    blend = 0
    nl = (1,1)
    dx_min = 0.1

    idx, _ = Mesh_maker.Get_nodes(flow, nl, dx_min, blend)
    
    assert len(idx) == 400
    
    flow = flow_class()
    blend = 0
    nl = (1,1)
    dx_min = 1

    idx, _ = Mesh_maker.Get_nodes(flow, nl, dx_min, blend)

    assert len(idx) == 200
    
def test_Graph_flow_model():
    name_textfile_flow = 'maaktnietuit'
    Load_flow = flow_class
    blend = 0
    nl = (1,1)
    dx_min = 0.5
    vship = np.array([[4],[5]])
    WD_min = np.array([1,1])
    WVPI = np.array([5000,6000])
    number_of_neighbor_layers = 1

    Roadmap = Mesh_maker.Graph_flow_model(name_textfile_flow, 
                                          dx_min, blend, 
                                          nl, 
                                          number_of_neighbor_layers, 
                                          vship, 
                                          Load_flow, 
                                          WD_min, 
                                          WVPI

                                           )
    
    clear_output()
    
    assert Roadmap.v.shape == (400,10)
    assert Roadmap.t.shape[0] == 10
    
def test_Graph_flow_model_with_indices():
    nodes_index = np.loadtxt('tests/Data/idx.csv', dtype=int)
    name_textfile_flow = 'maaktnietuit'
    Load_flow = flow_class
    blend = 0
    nl = (1,1)
    dx_min = 0.5
    vship = np.array([[4],[5]])
    WD_min = np.array([1,1])
    WVPI = np.array([5000,6000])
    number_of_neighbor_layers = 1

    Roadmap = Mesh_maker.Graph_flow_model(name_textfile_flow, 
                                          dx_min, blend, 
                                          nl, 
                                          number_of_neighbor_layers, 
                                          vship, 
                                          Load_flow, 
                                          WD_min, 
                                          WVPI,
                                          nodes_index = nodes_index
                                         )
    
    clear_output()
    
    assert Roadmap.v.shape == (400,10)
    assert Roadmap.t.shape[0] == 10