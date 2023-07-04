"""This mixin aims to formulate port accessibilty based on water, bottom, and ship-related factors"""
from .simpy_object import SimpyObject


class HasDraught(SimpyObject):
    def __init__(self, draught, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.draught = draught
        self.UKC = 0.1 * draught  # When the UKC policy is 10% at the port

    def get_draught(self):
        return self.draught

    def get_UKC(self):
        return self.UKC


class HasWaterLevel(SimpyObject):
    def __init__(self, water_level, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.water_level = water_level

    def get_water_level(self):
        state = {}
        if hasattr(super(), "get_water_level"):
            state = super().get_water_level()

        state.update({"water_level": self.water_level.get_water_level()})
        return state


class HasTide(SimpyObject):
    def __init__(self, tide_height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tide_height = tide_height

    def get_tide_height(self):
        state = {}
        if hasattr(super(), "get_tide_height"):
            state = super().get_tide_height()

        state.update({"tide height": self.tide_height.get_tide_height()})
        return state


class HasMaintainedDepth(SimpyObject):
    def __init__(self, maintained_depth, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maintained_depth = maintained_depth

    def get_maintained_depth(self):
        state = {}
        if hasattr(super(), "maintained_depth"):
            state = super().get_maintained_depth()

        state.update({"maintained depth": self.maintained_depth.get_maintained_depth()})
        return state


class HasBedLevel(SimpyObject):
    def __init__(self, bathymetry, sedimentation_rate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bathymetry = bathymetry
        self.sedimentation_rate = sedimentation_rate

    def get_bed_level(self):
        state = {}
        if hasattr(super(), "get_bed_level"):
            state = super().get_bed_level()

        state.update(
            {
                "bed level": self.sedimentation_rate.get_bed_level()
                + self.bathymetry.get_bed_level()
            }
        )
        return state
