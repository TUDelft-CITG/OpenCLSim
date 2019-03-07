import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import pickle

def printtime(t):
    print("Route completed in",int(t/3600), "hour", 
      int((t-int(t/3600)*3600)/60), "minutes and", 
      np.round(t -int(t/3600)*3600- int((t-int(t/3600)*3600)/60)*60, 2), "seconds")
    return
                           
