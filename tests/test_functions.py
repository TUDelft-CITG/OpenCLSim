import halem.Mesh_maker as Mesh_maker
import halem.Functions as Functions
import halem.Calc_path as Calc_path
import halem.Flow_class as Flow_class
from scipy.spatial import Delaunay

import pytest
import numpy as np
import geopy.distance

def coord_a():
    return (0,0)

def coord_b():
    return (0,1)

def vship():
    return 5

def v(mag):
    v = np.array([[0,0,1,-1]])
    v = mag * np.concatenate((v,v), axis = 0)
    return v

def u(mag):
    u = np.array([[1,-1,0,0]])
    u = mag * np.concatenate((u,u), axis = 0)
    return u

class flow():
    def __init__(self,mag, name =  'maaktnietuit'):
        self.t = np.arange(0,100) + 1558077464
        self.nodes = np.array([(0,0),
                          (0,1),
                          (1,1),
                          (0,3),])
        
        self.tria = Delaunay(self.nodes)
        
        self.WD = np.ones((len(self.t), len(self.nodes)))*1000
        self.u = np.ones((len(self.t), len(self.nodes)))*mag       
        self.v = np.ones((len(self.t), len(self.nodes)))*0
        self.WWL = 1
        self.LWL = 1
        self.ukc = 1
        
        
def test_haversine():
    dist = Functions.haversine(coord_a(), coord_a())
    dist1 = Functions.haversine(coord_a(), coord_b())
    dist2 = geopy.distance.geodesic(coord_a(), coord_b()).m

    assert dist == 0 
    assert abs(dist1 - dist2) < 0.01*dist1
    
def test_costfunction_space():
    edge = (0,1)
    WD_min = 0
    nodes = [coord_a(), coord_b()]
    mask = np.full((u(1).shape), False)
    L = Functions.costfunction_spaceseries(edge, vship(), WD_min, flow(0) )
    dist = Functions.haversine(coord_a(), coord_b()) * np.ones(u(1).shape[1])
    np.testing.assert_array_equal(L,dist)
    
def test_costfunction_time():
    mag = 3
    WD_min = 1
    edge = (0,1)
    nodes = [coord_a(), coord_b()]
    mask = np.full((u(mag).shape), False)
    WVPI= 1
    L = Functions.costfunction_timeseries(edge, vship(), WD_min, flow(3), WVPI )

    VSHIP = Functions.Squat(flow(3).WD[0],WD_min,vship(), flow(3).LWL, flow(3).WWL, flow(3).ukc, WVPI)

    VV = np.array([VSHIP[0] + mag, VSHIP[0] + mag, VSHIP[0] + mag, VSHIP[0] + mag ])
    dist1 = Functions.haversine(coord_a(), coord_b())
    dist = dist1/VV

    np.testing.assert_array_equal(L,dist)