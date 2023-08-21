"""This mixin aims to formulate port accessibilty based on water, bottom, and ship-related factors
   The main idea behind these class objects is to ensure that the available water depth is higher than the required water depth.
   The required water depth is calculated by measuring the distance between maximum draught and actual water level.
"""
from .simpy_object import SimpyObject

# Ship-related factors
class HasDraught(SimpyObject):
    def __init__(self, draught, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.draught = draught
        self.UKC = 0.1 * draught  # When the UKC policy is 10% at the port

    def get_draught(self):
        return self.draught

    def get_UKC(self):
        return self.UKC
    
    @property
    def required_water_depth(self):
        return self.draught + self.UKC

# Water level-related factors
class HasActualWaterLevel(SimpyObject):
    def __init__(self, AWL, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AWL = AWL

    def get_AWL(self):
        state = {}
        if hasattr(super(), "get_AWL"):
            state = super().get_AWL()

        state.update({"AWL": self.AWL.get_AWL()})
        return state

class HasLowestAstronomicalTide(SimpyObject):
    def __init__(self, LAT, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.LAT = LAT

    def get_LAT(self):
        state = {}
        if hasattr(super(), "get_LAT"):
            state = super().get_LAT()

        state.update({"LAT": self.LAT.get_LAT()})
        return state

# Bottom-related factors
class HasManitainedBedLevel(SimpyObject):
    def __init__(self, MBL, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.MBL = MBL

    def get_MBL(self):
        state = {}
        if hasattr(super(), "get_MBL"):
            state = super().get_MBL()

        state.update({"MBL": self.MBL.get_MBL()})
        return state

# Determine the navigability of vessels 
class HasNavigability(SimpyObject):
    def __init__(self, AWL, LAT, MBL, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AWL = AWL
        self.LAT = LAT
        self.MBL = MBL

    @property
    def required_water_depth(self):
        required_water_depth = self.AWL - self.MBL - self.LAT
        return required_water_depth
