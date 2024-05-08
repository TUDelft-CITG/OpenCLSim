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

class HasTide(SimpyObject):
    def __init__(self, UKC, T, *args, **kwargs):
        """
        Support for tide.
        UKC: under keel clearance [m]
        T: draught of the vessel [m]
        """
        super().__init__(*args, **kwargs)
        # TODO: make consistent or share with opentnsim
        self.UKC = UKC
        self.T = T
