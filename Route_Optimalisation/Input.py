import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import main
import pickle


class Has_start_and_target:
    def __init__(self, Ng,Lf,Bf, x_start,y_start,x_target,y_target,vship, *args, **kwargs):
        super().__init__(Lf,Bf,*args,**kwargs)
        self.x_start = x_start
        self.y_start = y_start

        self.x_target = x_target
        self.y_target = y_target

        self.vship = vship
        self.Ng = Ng

        self.L = np.absolute(self.x_target - self.x_start)*1.25
        self.B = np.absolute(self.y_target - self.y_start)*1.25

        self.N = self.Ng
        self.M = self.Ng

        self.dx = self.L/self.N
        self.dy = self.B/self.M

        self.n_start = int(self.L * 0.1 / self.dx)
        self.n_target = int(self.L * 0.9 / self.dx)

        self.m_start = int(self.B * 0.1 / self.dy)
        self.m_target = int(self.B * 0.9 / self.dy)
        
class Has_flow_testcase:
    def __init__(self, Lf, Bf, Nf, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.Nf = Nf
        X1, Y1 = np.mgrid[0:Nf, 0:Nf]

        self.Xf = X1 * Lf/Nf
        self.Yf = Y1 * Bf/Nf
        
        self.flow_u_input = np.cos(np.pi*self.Yf/Lf)
        self.flow_v_input = -np.cos(np.pi*self.Xf/Bf)
        self.speed_input = np.sqrt(self.flow_u_input**2, self.flow_v_input**2)

        
