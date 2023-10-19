from .simpy_object import SimpyObject

class HasDredging(SimpyObject):
    def __init__(self, ABL, DCL, DBL, SR=0, *args, **kwargs):
        """
        Support for dredged bed level.
        ABL: actual bed level [m]
        DCL: Dredge criterion level [m]
        DBL: Dredge bed level [m]
        SR: Sedimentation rate [m/s]
        """
        super().__init__(*args, **kwargs)
        self.ABL = ABL
        self.DCL = DCL
        self.DBL = DBL
        self.SR = SR
