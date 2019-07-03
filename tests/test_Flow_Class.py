import halem.Mesh_maker as Mesh_maker
import halem.Functions as Functions
import halem.Calc_path as Calc_path
import halem.Flow_class as Flow_class

import pytest
import numpy as np


def test_nodes_on_land_Waddensea():
    nodes = np.zeros((10,2))
    WD = np.zeros((10,20))
    u = 1.0*WD
    v = 1.0*WD
    new_nodes,new_u,new_v,new_WD = Flow_class.nodes_on_land_Waddensea(nodes,u,v,WD)


    assert new_nodes.shape == (212, 2)
    assert new_WD.shape == (212,20)
    assert new_u.shape == (212,20)
    assert new_v.shape == (212,20)

    np.testing.assert_array_equal(new_WD, np.zeros(new_WD.shape))
    np.testing.assert_array_equal(new_v, np.zeros(new_v.shape))
    np.testing.assert_array_equal(new_u, np.zeros(new_u.shape))