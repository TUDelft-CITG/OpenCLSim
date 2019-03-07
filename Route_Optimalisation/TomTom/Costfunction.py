import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import TomTom.main as main
import TomTom.Create_Graph as Create_Graph
import pickle

class Has_costfunction_space:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.costfunction = "space"
    
    def weight(self, a, b, Data):
        super().__init__()
        (ns, ms) = a
        (ng, mg) = b
        L = np.sqrt(((ng-ns)*Data.dx)**2 + ((mg-ms)*Data.dy)**2)
        return L

    def print_score(self, score):
        super().__init__()
        print("The total lengt of the route is:",round(score,1),"meters")

class Has_costfunction_time:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.costfunction = "time"
    def weight(self, a, b, Data,  flow_u, flow_v):
        super().__init__()

        (ns, ms) = a
        (ng, mg) = b
        ns = int(ns)
        ms = int(ms)
        ng = int(ng)
        mg = int(mg)

        v_w = (flow_v[ns,ms] + flow_v[ng,mg])/2
        u_w = (flow_u[ns,ms] + flow_u[ng,mg])/2
        U_w = (u_w**2 + v_w**2)**0.5

        alpha1 = np.arctan2((mg-ms),(ng-ns))
        alpha2 = np.arctan2(v_w , u_w) - alpha1

        n_w = U_w * np.sin(alpha2)
        s_w = U_w * np.cos(alpha2)
        s_t = s_w + (Data.vship ** 2 -  n_w**2) ** 0.5

        u_t = np.cos(alpha1)*s_t
        v_t = np.sin(alpha1)*s_t

        L = np.sqrt(((ng-ns)*Data.dx)**2 + ((mg-ms)*Data.dy)**2)
        U_t = (u_t**2 + v_t**2)**0.5
        t = L/U_t
        return t

    def print_score(self, t):
        super().__init__()
        print("Route completed in",int(t/3600), "hour", 
              int((t-int(t/3600)*3600)/60), "minutes and", 
              np.round(t -int(t/3600)*3600- int((t-int(t/3600)*3600)/60)*60, 2), "seconds")
    


    