# -*- coding: utf-8 -*-

"""Main module."""

# package(s) related to time, space and id
import json
import logging
import uuid
import itertools
from enum import Enum

# you need these dependencies (you can get these from anaconda)
# package(s) related to the simulation
import simpy
import networkx as nx

# spatial libraries
import pyproj
import shapely.geometry

# additional packages
import math
import datetime
import time
import copy
import numpy as np
import pandas as pd
from operator import itemgetter
from abc import ABC

from .utils import subcycle_repetitions

logger = logging.getLogger(__name__)


class SimpyObject:
    """General object which can be extended by any class requiring a simpy environment

    env: a simpy Environment
    """

    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env


class DebugArgs:
    """Object that logs if leftover args are passed onto it.
    """

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            message = "leftover arguments passed to {}, args: {},  kwargs: {}"
            logger.warn(message.format(self, args, kwargs))
        super().__init__()


class Identifiable:
    """Something that has a name and id

    name: a name
    id: a unique id generated with uuid"""

    def __init__(self, name, ID=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        # generate some id, in this case based on m
        self.id = ID if ID else str(uuid.uuid1())


class Locatable:
    """Something with a geometry (geojson format)

    geometry: can be a point as well as a polygon"""

    def __init__(self, geometry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.geometry = geometry
        self.wgs84 = pyproj.Geod(ellps="WGS84")

    def is_at(self, locatable, tolerance=100):
        current_location = shapely.geometry.asShape(self.geometry)
        other_location = shapely.geometry.asShape(locatable.geometry)
        _, _, distance = self.wgs84.inv(
            current_location.x, current_location.y, other_location.x, other_location.y
        )

        return distance < tolerance


class EventsContainer(simpy.FilterStore):
    def __init__(self, env, store_capacity=1, *args, **kwargs):
        super().__init__(env, capacity=store_capacity)
        self._env = env
        self._get_available_events = {}
        self._put_available_events = {}
        print("init")

    def initialize(self, init=0, capacity=0):
        self.put(init, capacity)

    def initialize_container(self, initials):
        for item in initials:
            print(item)
            assert "id" in item
            assert "capacity" in item
            assert "level" in item
            super().put(item)

    def get_available(self, amount, id_="default"):
        print("start get_available")
        if self.get_level(id_) >= amount:
            return self._env.event().succeed()
        if id_ in self._get_available_events:
            if amount in self._get_available_events[id_]:
                return self._get_available_events[id_][amount]
        # else case: id_ is not in self._get_available_events
        new_event = self._env.event()
        self._get_available_events[id_] = {}
        self._get_available_events[id_][amount] = new_event
        return new_event

    def get_capacity(self, id_="default"):
        # print(f"start get_capacity id_ {id_}")
        # print(self.items)
        if self.items == None:
            return 0
        res = [item["capacity"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def get_level(self, id_="default"):
        # print(f"start get_level with id_ {id_}")
        # print(self.items)
        if self.items == None:
            return 0
        res = [item["level"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def put_available(self, amount, id_="default"):
        print("start put_available")
        if self.get_capacity(id_) - self.get_level(id_) >= amount:
            print("succeed")
            return self._env.event().succeed()
        if id_ in self._put_available_events:
            print("check put_available events")
            if amount in self._put_available_events:
                return self._put_available_events[amount]
        print("register new event ")
        new_event = self._env.event()
        self._put_available_events[id_] = {}
        self._put_available_events[id_][amount] = new_event
        return new_event

    def get_empty_event(self, start_event=False, id_="default"):
        if not start_event:
            return self.put_available(self.get_capacity(id_), id_)
        elif start_event.processed:
            return self.put_available(self.get_capacity(id_), id_)
        else:
            return self._env.event()

    def get_full_event(self, start_event=False, id_="default"):
        print(f"get_full_event : {id_}")
        if not start_event:
            return self.get_available(self.get_capacity(id_), id_)
        elif start_event.processed:
            return self.get_available(self.get_capacity(id_), id_)
        else:
            return self._env.event()

    @property
    def empty_event(self):
        return self.put_available(self.get_capacity())

    @property
    def full_event(self):
        return self.get_available(self.get_capacity())

    def put(self, amount, capacity=0, id_="default"):
        current_amount = 0
        if len(self.items) > 0:
            status = super().get(lambda status: status["id"] == id_)
            print(status)
            # if status.ok:
            if status.triggered:
                status = status.value
                if "capacity" in status:
                    capacity = status["capacity"]
                if "level" in status:
                    current_amount = status["level"]
            else:
                raise Exception(
                    f"Failed to derive the previous version of container {id_}"
                )
        # this is a fall back in case the container is used with default
        put_event = super().put(
            {"id": id_, "level": current_amount + amount, "capacity": capacity}
        )
        put_event.callbacks.append(self.put_callback)
        return put_event

    def put_callback(self, event, id_="default"):
        print(f"put_callback - id_ {event.item['id']}")
        if isinstance(event, simpy.resources.store.StorePut):
            if "id" in event.item:
                id_ = event.item["id"]
        print(self._get_available_events)
        if id_ in self._get_available_events:
            for amount in sorted(self._get_available_events[id_]):
                print(f"amount :{amount}")
                # if isinstance(self, ReservationContainer):
                #    if self.get_expected_level(id_) >= amount:
                #        self._get_available_events[id_][amount].succeed()
                #        del self._get_available_events[id_][amount]
                # el
                if self.get_level(id_) >= amount:
                    if id_ in self._get_available_events:
                        self._get_available_events[id_][amount].succeed()
                        del self._get_available_events[id_][amount]
                else:
                    return

    def get(self, amount, id_="default"):
        print(f"start get {amount}")
        store_status = super().get(lambda state: state["id"] == id_).value
        print(f"store_status {store_status}")
        # print(f"store_status value {store_status.value}")
        store_status["level"] = store_status["level"] - amount
        get_event = super().put(store_status)
        get_event.callbacks.append(self.get_callback)
        print(f"end get {amount}")
        return get_event

    def get_callback(self, event, id_="default"):
        print(f"get_callback - id_ {event}")
        # it is confusing that this is checking for storeput while doing a get
        # the reason is that subtracting from a container requires to get the complete
        # content of a container and then add the remaining content of the container
        # which creates a storeput
        if isinstance(event, simpy.resources.store.StorePut):
            if "id" in event.item:
                id_ = event.item["id"]
        print("start get_callback")
        print(self._put_available_events)
        if id_ in self._put_available_events:
            for amount in sorted(self._put_available_events[id_]):
                # if isinstance(self, ReservationContainer):
                #    if self.get_capacity(id_) - self.get_expected_level(id_) >= amount:
                #        self._put_available_events[amount].succeed()
                #        del self._put_available_events[amount]
                # el
                if self.get_capacity(id_) - self.get_level(id_) >= amount:
                    if id_ in self._put_available_events:
                        self._put_available_events[id_][amount].succeed()
                        del self._put_available_events[id_][amount]
                else:
                    return

    @property
    def container_list(self):
        container_ids = []
        if len(self.items) > 0:
            container_ids = [item["id"] for item in self.items]
        return container_ids


class EventsObjects(SimpyObject):
    def __init__(
        self,
        env,
        objet_level,
        object_capacity=1,
        object_type="default_type",
        object_id=None,
        state="default_state",
        *args,
        **kwargs,
    ):
        super().__init__(env)
        assert object_capacity > 0
        assert ((object_id != None) and (object_capacity == 1)) or (object_id == None)
        self.object_id = object_id
        self.object_capacity = object_capacity
        self.object_level = object_level
        self.object_type = object_type
        self.object_state = object_state  # state can be any identifier, like e.g. the different locations an object has to go through

    def is_equal(
        self, state="default_state", object_type="default_type", object_id=None
    ):
        return (
            self.state == state
            and self.object_type == object_type
            and self.object_id == object_id
        )

    def get_level(self):
        return self.object_level

    def get_capacity(self):
        return self.object_capacity


class EventsStore(simpy.FilterStore):
    def __init__(self, env, store_capacity=1000, *args, **kwargs):
        super().__init__(env, capacity=store_capacity)
        self._get_available_events = {}
        self._put_available_events = {}
        print("init")

    def initialize_container(self, initials):
        for item in initials:
            assert isinstance(item, EventsObject)
            super().put(item)

    def peek(self, amount, selection_function, *args):
        container_objects = []
        if len(self.items) > 0:
            container_objects = [
                item for item in self.items if selection_function(item, *args)
            ]
        return container_objects

    def get_available(
        self, amount, state="default_state", object_type="default_type", object_id=None
    ):
        print("start get_available")
        object_ = (
            super().get(lambda obj: obj.is_equal(state, object_type, object_id)).value
        )

        if self.get_level(id_) >= amount:
            return self._env.event().succeed()
        if id_ in self._get_available_events:
            if amount in self._get_available_events[id_]:
                return self._get_available_events[id_][amount]
        # else case: id_ is not in self._get_available_events
        new_event = self._env.event()
        self._get_available_events[id_] = {}
        self._get_available_events[id_][amount] = new_event
        return new_event

    def get_capacity(self, id_="default"):
        # print(f"start get_capacity id_ {id_}")
        # print(self.items)
        if self.items == None:
            return 0
        res = [item["capacity"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def get_level(self, id_="default"):
        # print(f"start get_level with id_ {id_}")
        # print(self.items)
        if self.items == None:
            return 0
        res = [item["level"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def put_available(self, amount, id_="default"):
        if self.get_capacity(id_) - self.get_level(id_) >= amount:
            return self._env.event().succeed()
        if id_ in self._put_available_events:
            if amount in self._put_available_events:
                return self._put_available_events[amount]
        new_event = self._env.event()
        self._put_available_events[id_] = {}
        self._put_available_events[id_][amount] = new_event
        return new_event

    def get_empty_event(self, start_event=False, id_="default"):
        if not start_event:
            return self.empty_event
        elif start_event.processed:
            return self.empty_event
        else:
            return self._env.event()

    def get_full_event(self, start_event=False, id_="default"):
        if not start_event:
            return self.full_event
        elif start_event.processed:
            return self.full_event
        else:
            return self._env.event()

    @property
    def empty_event(self):
        id_ = "default"
        return self.put_available(self.get_capacity())

    @property
    def full_event(self):
        return self.get_available(self.get_capacity())

    def put(self, amount, capacity=0, id_="default"):
        if len(self.items) > 0:
            status = super().get(lambda status: status["id"] == id_)
            pprint(status)
            # if status.ok:
            if status.triggered:
                status = status.value
                if "capacity" in status:
                    capacity = status["capacity"]
            else:
                raise Exception(
                    f"Failed to derive the previous version of container {id_}"
                )
        # this is a fall back in case the container is used with default
        put_event = super().put({"id": id_, "level": amount, "capacity": capacity})
        put_event.callbacks.append(self.put_callback)
        return put_event

    def put_callback(self, event, id_="default"):
        for amount in sorted(self._get_available_events):
            if isinstance(self, ReservationContainer):
                if self.get_expected_level(id_) >= amount:
                    self._get_available_events[amount].succeed()
                    del self._get_available_events[amount]
            elif self.get_level(id_) >= amount:
                if id_ in self._get_available_events:
                    self._get_available_events[id_][amount].succeed()
                    del self._get_available_events[id_][amount]
            else:
                return

    def get(self, amount, id_="default"):
        print(f"start get {amount}")
        store_status = super().get(lambda state: state["id"] == id_).value
        print(f"store_status {store_status}")
        # print(f"store_status value {store_status.value}")
        store_status["level"] = store_status["level"] - amount
        get_event = super().put(store_status)
        get_event.callbacks.append(self.get_callback)
        print(f"end get {amount}")
        return get_event

    def get_callback(self, event, id_="default"):
        print("start get_callback")
        for amount in sorted(self._put_available_events):
            if isinstance(self, ReservationContainer):
                if self.get_capacity(id_) - self.get_expected_level(id_) >= amount:
                    self._put_available_events[amount].succeed()
                    del self._put_available_events[amount]
            elif self.get_capacity(id_) - self.get_level(id_) >= amount:
                if id_ in self._put_available_events:
                    self._put_available_events[id_][amount].succeed()
                    del self._put_available_events[id_][amount]
            else:
                return

    @property
    def container_list(self):
        container_ids = []
        if len(self.items) > 0:
            container_ids = [item["id"] for item in self.items]


class ReservationContainer(EventsContainer):
    def __init__(self, env, store_capacity=1, *args, **kwargs):
        super().__init__(env, capacity=store_capacity, *args, **kwargs)
        # super().__init__(*args, **kwargs)

        # self.expected_level = init
        self._content_available = {}
        self._space_available = {}

    def get_expected_level(self, id_="default__reservation"):
        if self.items == None:
            return 0
        res = [item["level"] for item in self.items if item["id"] == id_]
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return 0

    def reserve_put(self, amount, id_="default__reservation"):
        if self.get_expected_level(id_) + amount > self.get_capacity(Id_):
            raise RuntimeError("Attempting to reserve unavailable space")

        # self.expected_level += amount
        self.put(self.get_expected_level(id_) + amount, id_=id_)

        if id_ in self._content_available:
            if (
                self._content_available[id_] is not None
                and not self._content_available[id_].triggered
                and amount > 0
            ):
                self._content_available[id_].succeed()

    def reserve_get(self, amount, id_="default__reservation"):
        if self.get_expected_level(id_) < amount:
            raise RuntimeError("Attempting to reserve unavailable content")

        # self.expected_level -= amount
        self.get(amount, id_=id_)

        if id_ in self._space_available:
            if (
                self._space_available[id_] is not None
                and not self._space_available[id_].triggered
                and amount > 0
            ):
                self._space_available[id_].succeed()

    def reserve_put_available(self, id_="default__reservation"):
        if self.get_expected_level(id_) < self.get_capacity(id_):
            return self._env.event().succeed()

        if self._space_available is not None and not self._space_available.triggered:
            return self._space_available

        self._space_available = self._env.event()
        return self._space_available

    def reserve_get_available(self, id_="default__reservation"):
        if self.get_expected_level(id_) > 0:
            return self._env.event().succeed()

        if (
            id_ in self._content_available
            and self._content_available[id_] is not None
            and not self._content_available[id_].triggered
        ):
            return self._content_available[id_]

        self._content_available[id_] = self._env.event()
        return self._content_available[id_]


class HasContainer(SimpyObject):
    """Container class

    capacity: amount the container can hold
    level: amount the container holds initially
    container: a simpy object that can hold stuff"""

    def __init__(self, store_capacity=1, capacity=0, level=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        # container_class = type(
        #    "CombinedContainer", (EventsContainer, ReservationContainer), {}
        # )
        container_class = EventsContainer
        self.container = container_class(self.env, store_capacity=store_capacity)
        if capacity > 0:
            print(f"level: {level}")
            self.container.initialize(capacity=capacity, init=level)
            # self.container.initialize_reservation(capacity=capacity, init=level)
            print("completed init")


class HasMultiContainer(HasContainer):
    """Container class

    capacity: amount the container can hold
    level: amount the container holds initially
    container: a simpy object that can hold stuff"""

    def __init__(self, initials, store_capacity=10, *args, **kwargs):
        super().__init__(store_capacity=store_capacity, *args, **kwargs)
        self.container.initialize_container(initials)


class EnergyUse(SimpyObject):
    """EnergyUse class

    energy_use_sailing:   function that specifies the fuel use during sailing activity   - input should be time
    energy_use_loading:   function that specifies the fuel use during loading activity   - input should be time
    energy_use_unloading: function that specifies the fuel use during unloading activity - input should be time

    Example function could be as follows.
    The energy use of the loading event is equal to: duration * power_use.

    def energy_use_loading(power_use):
        return lambda x: x * power_use
    """

    def __init__(
        self,
        energy_use_sailing=None,
        energy_use_loading=None,
        energy_use_unloading=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.energy_use_sailing = energy_use_sailing
        self.energy_use_loading = energy_use_loading
        self.energy_use_unloading = energy_use_unloading


class HasCosts:
    """
    Add cost properties to objects
    """

    def __init__(
        self,
        dayrate=None,
        weekrate=None,
        mobilisation=None,
        demobilisation=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        assert dayrate != weekrate
        self.dayrate = dayrate if dayrate else weekrate / 7

        self.mobilisation = mobilisation if mobilisation else 0
        self.demobilisation = demobilisation if demobilisation else 0

    @property
    def cost(self):

        cost = (
            (self.log["Timestamp"][-1] - self.log["Timestamp"][0]).total_seconds()
            / 3600
            / 24
            * self.dayrate
            if self.log["Timestamp"]
            else 0
        )

        return cost + self.mobilisation + self.demobilisation


class HasPlume(SimpyObject):
    """Using values from Becker [2014], https://www.sciencedirect.com/science/article/pii/S0301479714005143.

    The values are slightly modified, there is no differences in dragead / bucket drip / cutterhead within this class
    sigma_d = source term fraction due to dredging
    sigma_o = source term fraction due to overflow
    sigma_p = source term fraction due to placement
    f_sett  = fraction of fines that settle within the hopper
    f_trap  = fraction of fines that are trapped within the hopper
    """

    def __init__(
        self,
        sigma_d=0.015,
        sigma_o=0.1,
        sigma_p=0.05,
        f_sett=0.5,
        f_trap=0.01,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.sigma_d = sigma_d
        self.sigma_o = sigma_o
        self.sigma_p = sigma_p
        self.f_sett = f_sett
        self.f_trap = f_trap

        self.m_r = 0


class HasSpillCondition(SimpyObject):
    """Condition to stop dredging if certain spill limits are exceeded

    limit = limit of kilograms spilled material
    start = start of the condition
    end   = end of the condition
    """

    def __init__(self, conditions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        limits = []
        starts = []
        ends = []

        if type(conditions) == list:
            for condition in conditions:
                limits.append(simpy.Container(self.env, capacity=condition.spill_limit))
                starts.append(time.mktime(condition.start.timetuple()))
                ends.append(time.mktime(condition.end.timetuple()))

        else:
            limits.append(simpy.Container(self.env, capacity=conditions.spill_limit))
            starts.append(time.mktime(conditions.start.timetuple()))
            ends.append(time.mktime(conditions.end.timetuple()))

        self.SpillConditions = pd.DataFrame.from_dict(
            {"Spill limit": limits, "Criterion start": starts, "Criterion end": ends}
        )

    def check_conditions(self, spill):
        tolerance = math.inf
        waiting = 0

        for i in self.SpillConditions.index:

            if (
                self.SpillConditions["Criterion start"][i] <= self.env.now
                and self.env.now <= self.SpillConditions["Criterion end"][i]
            ):
                tolerance = (
                    self.SpillConditions["Spill limit"][i].get_capacity()
                    - self.SpillConditions["Spill limit"][i].get_level()
                )

                if tolerance < spill:
                    waiting = self.SpillConditions["Criterion end"][i]

                while i + 1 != len(self.SpillConditions.index) and tolerance < spill:
                    if (
                        self.SpillConditions["Criterion end"][i]
                        == self.SpillConditions["Criterion start"][i + 1]
                    ):
                        tolerance = (
                            self.SpillConditions["Spill limit"][i + 1].get_capacity()
                            - self.SpillConditions["Spill limit"][i + 1].get_level()
                        )
                        waiting = self.SpillConditions["Criterion end"][i + 1]

                    i += 1

        return waiting


class SpillCondition:
    """Condition to stop dredging if certain spill limits are exceeded

    limit = limit of kilograms spilled material
    start = start of the condition
    end   = end of the condition
    """

    def __init__(self, spill_limit, start, end, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.spill_limit = spill_limit
        self.start = start
        self.end = end


class HasSpill(SimpyObject):
    """Using relations from Becker [2014], https://www.sciencedirect.com/science/article/pii/S0301479714005143."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    def spillDredging(
        self,
        processor,
        mover,
        density,
        fines,
        volume,
        dredging_duration,
        overflow_duration=0,
    ):
        """Calculate the spill due to the dredging activity

        density = the density of the dredged material
        fines   = the percentage of fines in the dredged material
        volume  = the dredged volume
        dredging_duration = duration of the dredging event
        overflow_duration = duration of the dredging event whilst overflowing

        m_t = total mass of dredged fines per cycle
        m_d = total mass of spilled fines during one dredging event
        m_h = total mass of dredged fines that enter the hopper

        m_o  = total mass of fine material that leaves the hopper during overflow
        m_op = total mass of fines that are released during overflow that end in dredging plume
        m_r  = total mass of fines that remain within the hopper"""

        m_t = density * fines * volume
        m_d = processor.sigma_d * m_t
        m_h = m_t - m_d

        m_o = (
            (overflow_duration / dredging_duration)
            * (1 - mover.f_sett)
            * (1 - mover.f_trap)
            * m_h
        )
        m_op = mover.sigma_o * m_o
        mover.m_r = m_h - m_o

        processor.log_entry(
            "fines released",
            self.env.now,
            m_d + m_op,
            self.geometry,
            processor.ActivityID,
        )

        return m_d + m_op

    def spillPlacement(self, processor, mover):
        """Calculate the spill due to the placement activity"""
        if isinstance(self, Log):
            processor.log_entry(
                "fines released",
                self.env.now,
                mover.m_r * processor.sigma_p,
                self.geometry,
                processor.ActivityID,
            )

        return mover.m_r * processor.sigma_p


class SoilLayer:
    """ Create a soillayer

    layer = layer number, 0 to n, with 0 the layer at the surface
    material = name of the dredged material
    density = density of the dredged material
    fines = fraction of total that is fine material
    """

    def __init__(self, layer, volume, material, density, fines, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.layer = layer
        self.volume = volume
        self.material = material
        self.density = density
        self.fines = fines


class HasSoil:
    """ Add soil properties to an object

    soil = list of SoilLayer objects
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.soil = {}

    def add_layer(self, soillayer):
        """Add a layer based on a SoilLayer object."""
        for key in self.soil:
            if key == "Layer {:04d}".format(soillayer.layer):
                print(
                    "Soil layer named **Layer {:04d}** already exists".format(
                        soillayer.layer
                    )
                )

        # Add soillayer to self
        self.soil["Layer {:04d}".format(soillayer.layer)] = {
            "Layer": soillayer.layer,
            "Volume": soillayer.volume,
            "Material": soillayer.material,
            "Density": soillayer.density,
            "Fines": soillayer.fines,
        }

        # Make sure that self.soil is always a sorted dict based on layernumber
        soil = copy.deepcopy(self.soil)
        self.soil = {}

        for key in sorted(soil):
            self.soil[key] = soil[key]

    def add_layers(self, soillayers):
        """Add a list layers based on a SoilLayer object."""
        for layer in soillayers:
            self.add_layer(layer)

    def total_volume(self):
        """Determine the total volume of soil."""
        total_volume = 0

        for layer in self.soil:
            total_volume += self.soil[layer]["Volume"]

        return total_volume

    def weighted_average(self, layers, volumes):
        """Create a new SoilLayer object based on the weighted average parameters of extracted layers.

        len(layers) should be len(volumes)"""
        densities = []
        fines = []
        name = "Mixture of: "

        for i, layer in enumerate(layers):
            if 0 < volumes[i]:
                densities.append(self.soil[layer]["Density"])
                fines.append(self.soil[layer]["Fines"])
                name += self.soil[layer]["Material"] + ", "
            else:
                densities.append(0)
                fines.append(0)

        return SoilLayer(
            0,
            sum(volumes),
            name.rstrip(", "),
            np.average(np.asarray(densities), weights=np.asarray(volumes)),
            np.average(np.asarray(fines), weights=np.asarray(volumes)),
        )

    def get_soil(self, volume):
        """Remove soil from self."""

        # If soil is a mover, the mover should be initialized with an empty soil dict after emptying
        if isinstance(self, Movable) and 0 == self.container.get_level():
            removed_soil = list(self.soil.items())[0]

            self.soil = {}

            return SoilLayer(
                0,
                removed_soil[1]["Volume"],
                removed_soil[1]["Material"],
                removed_soil[1]["Density"],
                removed_soil[1]["Fines"],
            )

        # In all other cases the soil dict should remain, with updated values
        else:
            removed_volume = 0
            layers = []
            volumes = []

            for layer in sorted(self.soil):
                if (volume - removed_volume) <= self.soil[layer]["Volume"]:
                    layers.append(layer)
                    volumes.append(volume - removed_volume)

                    self.soil[layer]["Volume"] -= volume - removed_volume

                    break

                else:
                    removed_volume += self.soil[layer]["Volume"]
                    layers.append(layer)
                    volumes.append(self.soil[layer]["Volume"])

                    self.soil[layer]["Volume"] = 0

            return self.weighted_average(layers, volumes)

    def put_soil(self, soillayer):
        """Add soil to self.

        Add a layer based on a SoilLayer object."""
        # If already soil available
        if self.soil:
            # Can be moveable --> mix
            if isinstance(self, Movable):
                pass

            # Can be site --> add layer or add volume
            else:
                top_layer = list(sorted(self.soil.keys()))[0]

                # If toplayer material is similar to added material --> add volume
                if (
                    self.soil[top_layer]["Material"] == soillayer.material
                    and self.soil[top_layer]["Density"] == soillayer.density
                    and self.soil[top_layer]["Fines"] == soillayer.fines
                ):

                    self.soil[top_layer]["Volume"] += soillayer.volume

                # If not --> add layer
                else:
                    layers = copy.deepcopy(self.soil)
                    self.soil = {}
                    self.add_layer(soillayer)

                    for key in sorted(layers):
                        layers[key]["Layer"] += 1
                        self.add_layer(
                            SoilLayer(
                                layers[key]["Layer"],
                                layers[key]["Volume"],
                                layers[key]["Material"],
                                layers[key]["Density"],
                                layers[key]["Fines"],
                            )
                        )

        # If no soil yet available, add layer
        else:
            self.add_layer(soillayer)

    def get_properties(self, amount):
        """Get the soil properties for a certain amount"""
        volumes = []
        layers = []
        volume = 0

        for layer in sorted(self.soil):
            if (amount - volume) <= self.soil[layer]["Volume"]:
                volumes.append(amount - volume)
                layers.append(layer)
                break
            else:
                volumes.append(self.soil[layer]["Volume"])
                layers.append(layer)
                volume += self.soil[layer]["Volume"]

        properties = self.weighted_average(layers, volumes)

        return properties.density, properties.fines


class HasAbstractWeather(ABC):
    """HasAbstractWeather class

    Abstract class, which provides a superclass for solutions 
    adding weather conditions to a project site
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""


class HasWeather(HasAbstractWeather):
    """HasWeather class

    Used to add weather conditions to a project site
    name: name of .csv file in folder

    year: name of the year column
    month: name of the month column
    day: name of the day column

    timestep: size of timestep to interpolate between datapoints (minutes)
    bed: level of the seabed / riverbed with respect to CD (meters)
    """

    def __init__(
        self,
        dataframe,
        timestep=10,
        bed=None,
        waveheight_column="Hm0 [m]",
        waveperiod_column="Tp [s]",
        waterlevel_column="Tide [m]",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.timestep = datetime.timedelta(minutes=timestep)

        data = {}
        for key in dataframe:
            series = (
                pd.Series(dataframe[key], index=dataframe.index)
                .fillna(0)
                .resample(self.timestep)
                .interpolate("linear")
            )

            data[key] = series.values

        data["Index"] = series.index
        self.metocean_data = pd.DataFrame.from_dict(data)
        self.metocean_data.index = self.metocean_data["Index"]
        self.metocean_data.drop(["Index"], axis=1, inplace=True)

        # Column names
        self.waveheight = waveheight_column
        self.waveperiod = waveperiod_column
        self.waterlevel = waterlevel_column
        self.waterdepth = "Water depth"

        if bed:
            self.metocean_data[self.waterdepth] = (
                self.metocean_data[waterlevel_column] - bed
            )


class HasAbstractWorkabilityCriteria(ABC):
    """Abstract HasWorkabilityCriteria class

    Used to add workability criteria
    """

    def __init__(self, criteria, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.criteria = criteria

    def check_weather_restriction(self, location, event):
        """Checks whether the execution of the event has to be delayed.
        If so a timeout event has to be issued, the corresponding logging has to be added 
        which will set the new starting time of the event to the time, when the execution
        actually can be performed."""

    def delay_processing(self, waiting):
        """Waiting must be a delay expressed in seconds"""
        self.log_entry(
            "delay activity",
            self.env.now,
            waiting,
            self.geometry,
            self.ActivityID,
            LogState.START,
        )
        yield self.env.timeout(np.max(waiting))
        self.log_entry(
            "delay processing",
            self.env.now,
            waiting,
            self.geometry,
            self.ActivityID,
            LogState.STOP,
        )


class HasWorkabilityCriteria(HasAbstractWorkabilityCriteria):
    """HasWorkabilityCriteria class

    Used to add workability criteria
    """

    def __init__(self, criteria, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.criteria = criteria
        self.work_restrictions = {}

    def calc_work_restrictions(self, location):
        # Loop through series to find windows
        for criterion in self.criteria:
            condition = location.metocean_data[criterion.condition]
            ix_condition = condition <= criterion.maximum
            ix_starts = ~ix_condition.values[:-1] & ix_condition.values[1:]
            ix_ends = ix_condition.values[:-1] & ~ix_condition.values[1:]
            if ix_condition[0]:
                ix_starts[0] = True
            if ix_starts.sum() > ix_ends.sum():
                ix_ends[-1] = True
            t_starts = condition.index[:-1][ix_starts]
            t_ends = condition.index[:-1][ix_ends]
            dt_windows = t_ends - t_starts
            ix_windows = dt_windows >= criterion.window_length * 3
            ranges = np.concatenate(
                (
                    t_starts[ix_windows].values.reshape((-1, 1)),
                    (t_ends[ix_windows] - criterion.window_length).values.reshape(
                        (-1, 1)
                    ),
                ),
                axis=1,
            )
            self.work_restrictions.setdefault(location.name, {}).setdefault(
                criterion.event_name, {}
            )[criterion.condition] = ranges

    def check_weather_restriction(self, location, event_name):

        if location.name not in self.work_restrictions.keys():
            self.calc_work_restrictions(location)

        if event_name in [criterion.event_name for criterion in self.criteria]:
            waiting = []

            for condition in self.work_restrictions[location.name][event_name]:
                ranges = self.work_restrictions[location.name][event_name][condition]

                t = datetime.datetime.fromtimestamp(self.env.now)
                t = pd.Timestamp(t).to_datetime64()
                i = ranges[:, 0].searchsorted(t)

                if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                    waiting.append(pd.Timedelta(0).total_seconds())
                elif i + 1 < len(ranges):
                    waiting.append(pd.Timedelta(ranges[i, 0] - t).total_seconds())
                else:
                    print("\nSimulation cannot continue.")
                    print("Simulation time exceeded the available metocean data.")
        if waiting:
            self.delay_processing(max(waiting))


class WorkabilityCriterion:
    """WorkabilityCriterion class

    Used to add limits to vessels (and therefore acitivities)
    event_name: name of the event for which this criterion applies
    condition: column name of the metocean data (Hs, Tp, etc.)
    minimum: minimum value
    maximum: maximum value
    window_length: minimal length of the window (minutes)"""

    def __init__(
        self,
        event_name,
        condition,
        minimum=math.inf * -1,
        maximum=math.inf,
        window_length=datetime.timedelta(minutes=60),
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.event_name = event_name
        self.condition = condition
        self.minimum = minimum
        self.maximum = maximum
        self.window_length = window_length


class HasDepthRestriction:
    """HasDepthRestriction class

    Used to add depth limits to vessels
    draught: should be a lambda function with input variable container.volume
    waves: list with wave_heights
    ukc: list with ukc, corresponding to wave_heights

    filling: filling degree [%]
    min_filling: minimal filling degree [%]
    max_filling: max filling degree [%]
    """

    def __init__(
        self,
        compute_draught,
        ukc,
        waves=None,
        filling=None,
        min_filling=None,
        max_filling=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        # Information required to determine whether vessel can access an area
        self.compute_draught = compute_draught
        self.ukc = ukc
        self.waves = waves

        # Information require to self-select filling degree
        if min_filling is not None and max_filling is not None:
            assert min_filling <= max_filling

        self.filling = int(filling) if filling is not None else None
        self.min_filling = int(min_filling) if min_filling is not None else int(0)
        self.max_filling = int(max_filling) if max_filling is not None else int(100)

        self.depth_data = {}

    def calc_depth_restrictions(self, location, processor):
        # Minimal waterdepth should be draught + ukc
        # Waterdepth is tide - depth site
        # For empty to full [20%, 25%, 30%, ... 90%, 95%, 100%]

        self.depth_data[location.name] = {}

        if not self.filling:
            filling_degrees = np.linspace(
                self.min_filling,
                self.max_filling,
                (self.max_filling - self.min_filling) + 1,
                dtype=int,
            )
        else:
            filling_degrees = [self.filling]

        for i in filling_degrees:
            filling_degree = i / 100

            # Determine characteristics based on filling
            draught = self.compute_draught(filling_degree)
            duration = datetime.timedelta(
                seconds=processor.unloading(
                    self,
                    location,
                    self.container.get_level()
                    + filling_degree * self.container.get_capacity(),
                )
            )

            # Make dataframe based on characteristics
            df = location.metocean_data.copy()
            df["Required depth"] = df[location.waveheight].apply(
                lambda s: self.calc_required_depth(draught, s)
            )
            series = pd.Series(df["Required depth"] <= df[location.waterdepth])

            # Loop through series to find windows
            index = series.index
            values = series.values
            in_range = False
            ranges = []

            for i, value in enumerate(values):
                if value == True:
                    if i == 0:
                        begin = index[i]
                    elif not in_range:
                        begin = index[i]

                    in_range = True
                elif in_range:
                    in_range = False
                    end = index[i]

                    if (end - begin) >= duration:
                        ranges.append(
                            (begin.to_datetime64(), (end - duration).to_datetime64())
                        )

            self.depth_data[location.name][filling_degree] = {
                "Volume": filling_degree * self.container.get_capacity(),
                "Draught": draught,
                "Ranges": np.array(ranges),
            }

    def viable_time_windows(self, fill_degree, duration, location):
        duration = datetime.timedelta(seconds=duration)
        draught = self.compute_draught(fill_degree)

        # Make dataframe based on characteristics
        df = location.metocean_data.copy()
        df["Required depth"] = df[location.waveheight].apply(
            lambda s: self.calc_required_depth(draught, s)
        )
        series = pd.Series(df["Required depth"] <= df[location.waterdepth])
        # Loop through series to find windows
        index = series.index
        values = series.values
        in_range = False
        ranges = []
        for i, value in enumerate(values):
            if value == True:
                if i == 0:
                    begin = index[i]
                elif not in_range:
                    begin = index[i]

                in_range = True
            elif in_range:
                in_range = False
                end = index[i]

                if (end - begin) >= duration:
                    ranges.append(
                        (begin.to_datetime64(), (end - duration).to_datetime64())
                    )

        self.depth_data[location.name][fill_degree] = {
            "Volume": fill_degree * self.container.get_capacity(),
            "Draught": draught,
            "Ranges": np.array(ranges),
        }

    def check_depth_restriction(self, location, fill_degree, duration):
        if location.name not in self.depth_data.keys():
            fill_degree = int(fill_degree * 100) / 100
            self.depth_data[location.name] = {}
            self.viable_time_windows(fill_degree, duration, location)

            ranges = self.depth_data[location.name][int(fill_degree * 100) / 100][
                "Ranges"
            ]

        elif fill_degree not in self.depth_data[location.name].keys():
            fill_degree = int(fill_degree * 100) / 100
            self.viable_time_windows(fill_degree, duration, location)

            ranges = self.depth_data[location.name][int(fill_degree * 100) / 100][
                "Ranges"
            ]

        else:
            ranges = self.depth_data[location.name][int(fill_degree * 100) / 100][
                "Ranges"
            ]

        if len(ranges) == 0:
            self.log_entry(
                "No actual allowable draught available - starting anyway",
                self.env.now,
                -1,
                self.geometry,
                self.ActivityID,
                LogState.START,
            )
            waiting = 0

        else:
            t = datetime.datetime.fromtimestamp(self.env.now)
            t = pd.Timestamp(t).to_datetime64()
            i = ranges[:, 0].searchsorted(t)

            if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                waiting = pd.Timedelta(0).total_seconds()
            elif i + 1 < len(ranges):
                waiting = pd.Timedelta(ranges[i, 0] - t).total_seconds()
            else:
                print("Exceeding time")
                waiting = 0

        if waiting != 0:
            self.log_entry(
                "waiting for tide",
                self.env.now,
                waiting,
                self.geometry,
                self.ActivityID,
                LogState.START,
            )
            yield self.env.timeout(waiting)
            self.log_entry(
                "waiting for tide",
                self.env.now,
                waiting,
                self.geometry,
                self.ActivityID,
                LogState.STOP,
            )

    def calc_required_depth(self, draught, wave_height):
        required_depth = np.nan

        if self.waves:
            for i, wave in enumerate(self.waves):
                if wave_height <= wave:
                    required_depth = self.ukc[i] + draught

            return required_depth

        else:
            return self.ukc + draught

    def check_optimal_filling(self, loader, unloader, origin, destination):
        # Calculate depth restrictions
        if not self.depth_data:
            if isinstance(origin, HasAbstractWeather):
                self.calc_depth_restrictions(origin, loader)
            if isinstance(destination, HasAbstractWeather):
                self.calc_depth_restrictions(destination, unloader)

        elif (
            origin.name not in self.depth_data.keys()
            or destination.name not in self.depth_data.keys()
        ):
            if isinstance(origin, HasAbstractWeather):
                self.calc_depth_restrictions(origin, loader)
            if isinstance(destination, HasAbstractWeather):
                self.calc_depth_restrictions(destination, unloader)

        # If a filling degee has been specified
        if self.filling is not None:
            return self.filling * self.container.get_capacity() / 100

        elif destination.name not in self.depth_data.keys():
            return self.container.get_capacity()

        # If not, try to optimize the load with regard to the tidal window
        else:
            loads = []
            waits = []
            amounts = []

            fill_degrees = self.depth_data[destination.name].keys()

            for filling in fill_degrees:
                ranges = self.depth_data[destination.name][filling]["Ranges"]

                if len(ranges) != 0:
                    # Determine length of cycle
                    loading = loader.loading(
                        origin,
                        destination,
                        filling * self.container.get_capacity()
                        - self.container.get_level(),
                    )

                    orig = shapely.geometry.asShape(origin.geometry)
                    dest = shapely.geometry.asShape(destination.geometry)
                    _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)
                    sailing_full = distance / self.compute_v(0)
                    sailing_full = distance / self.compute_v(filling)

                    duration = sailing_full + loading + sailing_full

                    # Determine waiting time
                    t = datetime.datetime.fromtimestamp(self.env.now + duration)
                    t = pd.Timestamp(t).to_datetime64()
                    i = ranges[:, 0].searchsorted(t)

                    if i > 0 and (ranges[i - 1][0] <= t <= ranges[i - 1][1]):
                        waiting = pd.Timedelta(0).total_seconds()
                    elif i != len(ranges):
                        waiting = pd.Timedelta(ranges[i, 0] - t).total_seconds()
                    else:
                        print("\nSimulation cannot continue.")
                        print("Simulation time exceeded the available metocean data.")

                        self.env.exit()

                    # In case waiting is always required
                    loads.append(filling * self.container.get_capacity())
                    waits.append(waiting)

                    if waiting < destination.timestep.total_seconds():
                        amounts.append(filling * self.container.get_capacity())

            # Check if there is a better filling degree
            if amounts:
                return max(amounts)
            elif loads:
                cargo = 0

                for i, _ in enumerate(loads):
                    if waits[i] == min(waits):
                        cargo = loads[i]

                return cargo

    @property
    def current_draught(self):
        return self.compute_draught(
            self.container.get_level() / self.container.get_capacity()
        )


class Movable(SimpyObject, Locatable):
    """Movable class

    Used for object that can move with a fixed speed
    geometry: point used to track its current location
    v: speed"""

    def __init__(self, v=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.v = v

    def move(self, destination, engine_order=1.0):
        """determine distance between origin and destination. 
        Yield the time it takes to travel based on flow properties and load factor of the flow."""

        # Log the start event
        self.log_sailing(log_state=LogState.START)

        # Determine the sailing_duration
        sailing_duration = self.sailing_duration(
            self.geometry, destination, engine_order
        )

        # Check out the time based on duration of sailing event
        yield self.env.timeout(sailing_duration)

        # Set mover geometry to destination geometry
        self.geometry = shapely.geometry.asShape(destination.geometry)

        # Debug logs
        logger.debug("  duration: " + "%4.2f" % (sailing_duration / 3600) + " hrs")

        # Log the stop event
        self.log_sailing(log_state=LogState.STOP)

    @property
    def current_speed(self):
        return self.v

    def log_sailing(self, log_state):
        """ Log the start or stop of the sailing event """

        if isinstance(self, HasContainer):
            list_ = self.container.container_list
            status = (
                "filled"
                if len(list_) > 0
                and sum([self.container.get_level(id_) for id_ in list_]) > 0
                else "empty"
            )
            self.log_entry(
                "sailing {}".format(status),
                self.env.now,
                self.container.get_level(),
                self.geometry,
                self.ActivityID,
                log_state,
            )
        else:
            self.log_entry(
                # "sailing {}".format(event),
                "sailing",
                self.env.now,
                -1,
                self.geometry,
                self.ActivityID,
                log_state,
            )

    def sailing_duration(self, origin, destination, engine_order, verbose=True):
        """ Determine the sailing duration """
        orig = shapely.geometry.asShape(self.geometry)
        dest = shapely.geometry.asShape(destination.geometry)
        _, _, distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)

        # Log the energy use
        self.energy_use(distance, self.current_speed * engine_order)

        return distance / (self.current_speed * engine_order)

    def energy_use(self, distance, speed):
        """ Determine the energy use """
        if isinstance(self, EnergyUse):
            # message depends on filling degree: if container is empty --> sailing empt
            if not isinstance(self, HasContainer) or self.container.get_level() == 0:
                message = "Energy use sailing empty"
                filling = 0.0
            else:
                message = "Energy use sailing filled"
                filling = self.container.get_level() / self.container.get_capacity()

            energy = self.energy_use_sailing(distance, speed, filling)
            self.log_entry(
                message, self.env.now, energy, self.geometry, self.ActivityID
            )


class ContainerDependentMovable(Movable, HasContainer):
    """ContainerDependentMovable class

    Used for objects that move with a speed dependent on the container level
    compute_v: a function, given the fraction the container is filled (in [0,1]), returns the current speed"""

    def __init__(self, compute_v, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_v = compute_v

    @property
    def current_speed(self):
        return self.compute_v(
            self.container.get_level() / self.container.get_capacity()
        )

    """AW: I think this method should be removed and only reside in a processor: shifting an amount requires an origin, a destination 
    and a processor, actually doing the transfer. """

    def determine_amount(self, origins, destinations, loader, unloader, filling=1):
        """ Determine the maximum amount that can be carried """

        # Determine the basic amount that should be transported
        all_amounts = {}
        all_amounts.update(
            {
                "origin." + origin.id: origin.container.get_expected_level(id_)
                for origin in origins
            }
        )
        all_amounts.update(
            {
                "destination."
                + destination.id: destination.container.get_capacity()
                - destination.container.get_expected_level(id_)
                for destination in destinations
            }
        )

        origin_requested = 0
        destination_requested = 0

        for key in all_amounts.keys():
            if "origin." in key:
                origin_requested += all_amounts[key]
            else:
                destination_requested += all_amounts[key]

        amount = min(
            self.container.get_capacity() * filling - self.container.get_level(),
            origin_requested,
            destination_requested,
        )

        # If the mover has a function to optimize its load, check if the amount should be changed
        if not hasattr(self, "check_optimal_filling"):
            return amount, all_amounts

        else:
            amounts = [amount]
            amounts.extend(
                [
                    self.check_optimal_filling(loader, unloader, origin, destination)
                    for origin, destination in itertools.product(origins, destinations)
                ]
            )

            return min(amounts), all_amounts

    def determine_schedule(self, amount, all_amounts, origins, destinations):
        """ 
        Define a strategy for passing through the origins and destinations
        Implemented is FIFO: First origins will start and first destinations will start.
        """
        self.vrachtbrief = {"Type": [], "ID": [], "Priority": [], "Amount": []}

        def update_vrachtbrief(typestring, id, priority, amount):
            """ Update the vrachtbrief """

            self.vrachtbrief["Type"].append(typestring)
            self.vrachtbrief["ID"].append(id)
            self.vrachtbrief["Priority"].append(priority)
            self.vrachtbrief["Amount"].append(amount)

        to_retrieve = 0
        to_place = 0

        # reserve the amount in origin an destination
        for origin in origins:
            if all_amounts["origin." + origin.id] == 0:
                continue
            elif all_amounts["origin." + origin.id] <= amount - to_retrieve:
                to_retrieve += all_amounts["origin." + origin.id]
                origin.container.reserve_get(all_amounts["origin." + origin.id])
                update_vrachtbrief(
                    "Origin", origin, 1, all_amounts["origin." + origin.id]
                )

            else:
                origin.container.reserve_get(amount - to_retrieve)
                update_vrachtbrief("Origin", origin, 1, amount - to_retrieve)
                break

        for destination in destinations:
            if all_amounts["destination." + destination.id] == 0:
                continue
            elif all_amounts["destination." + destination.id] <= amount - to_place:
                to_place += all_amounts["destination." + destination.id]
                destination.container.reserve_put(
                    all_amounts["destination." + destination.id]
                )
                update_vrachtbrief(
                    "Destination",
                    destination,
                    1,
                    all_amounts["destination." + destination.id],
                )

            else:
                destination.container.reserve_put(amount - to_place)
                update_vrachtbrief("Destination", destination, 1, amount - to_place)
                break

        return pd.DataFrame.from_dict(self.vrachtbrief).sort_values("Priority")


class MultiContainerDependentMovable(Movable, HasMultiContainer):
    """MultiContainerDependentMovable class

    Used for objects that move with a speed dependent on the container level
    compute_v: a function, given the fraction the container is filled (in [0,1]), returns the current speed"""

    def __init__(self, compute_v, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.compute_v = compute_v
        self.conainter_ids = self.container.container_list

    @property
    def current_speed(self):
        sum_level = 0
        sum_capacity = 0
        for id_ in self.container.container_list:
            sum_level = self.container.get_level(id_)
            sum_capacity = self.container.get_capacity(id_)
        fill_degree = sum_level / sum_capacity
        return self.compute_v(fill_degree)


class Routeable(Movable):
    """
    Moving folling a certain path
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    def determine_route(self, origin, destination):
        """ Determine the fastest sailing route based on distance """

        # If travelling on route is required, assert environment has a graph
        assert hasattr(self.env, "FG")

        # Origin is geom - convert to node on graph
        geom = nx.get_node_attributes(self.env.FG, "geometry")

        for node in geom.keys():
            if np.isclose(origin.x, geom[node].x, rtol=1e-8) and np.isclose(
                origin.y, geom[node].y, rtol=1e-8
            ):
                origin = node
                break

        if origin != node:
            raise AssertionError("The origin cannot be found in the graph")

        # Determine fastest route
        if hasattr(destination, "name"):
            if destination.name in list(self.env.FG.nodes):
                return nx.dijkstra_path(self.env.FG, origin, destination.name)

        for node in geom.keys():
            if (
                destination.geometry.x == geom[node].x
                and destination.geometry.y == geom[node].y
            ):
                destination = node
                return nx.dijkstra_path(self.env.FG, origin, destination)

        # If no route is returned
        raise AssertionError("The destination cannot be found in the graph")

    def determine_speed(self, node_from, node_to):
        """ Determine the sailing speed based on edge properties """
        edge_attrs = self.env.FG.get_edge_data(node_from, node_to)

        if not edge_attrs:
            return self.current_speed

        elif "maxSpeed" in edge_attrs.keys():
            return min(self.current_speed, edge_attrs["maxSpeed"])

        else:
            return self.current_speed

    def sailing_duration(self, origin, destination, engine_order, verbose=True):
        """ Determine the sailing duration based on the properties of the sailing route """

        # A dict with all nodes and the geometry property
        geom = nx.get_node_attributes(self.env.FG, "geometry")

        # Determine the shortest route from origin to destination
        route = self.determine_route(origin, destination)

        # Determine the duration and energy use of following the route
        duration = 0
        energy = 0

        for i, _ in enumerate(route):
            if i + 1 != len(route):
                orig = shapely.geometry.asShape(geom[route[i]])
                dest = shapely.geometry.asShape(geom[route[i + 1]])

                distance = self.wgs84.inv(orig.x, orig.y, dest.x, dest.y)[2]
                speed = self.determine_speed(route[i], route[i + 1])

                duration += distance / speed
                energy += self.energy_use(distance, speed)

                self.log_entry(
                    "Sailing", self.env.now + duration, 0, dest, self.ActivityID
                )

        # Log energy use
        self.log_energy_use(energy)

        return duration

    def energy_use(self, distance, speed):
        if isinstance(self, EnergyUse):
            return self.energy_use_sailing(distance, speed)
        else:
            return 0

    def log_energy_use(self, energy):
        if 0 < energy:
            self.log_entry(
                "Energy use sailing",
                self.env.now,
                energy,
                self.geometry,
                self.ActivityID,
            )


class ContainerDependentRouteable(ContainerDependentMovable, Routeable):
    """ContainerDependentRouteable class

    Used for objects that move with a speed dependent on the container level
    compute_v: a function, given the fraction the container is filled (in [0,1]), returns the current speed"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

    @property
    def current_speed(self):
        return self.compute_v(
            self.container.get_level() / self.container.get_capacity()
        )

    def energy_use(self, distance, speed):
        if isinstance(self, EnergyUse):
            filling = self.container.get_level() / self.container.get_capacity()
            return self.energy_use_sailing(distance, speed, filling)
        else:
            return 0

    def log_energy_use(self, energy):
        if 0 < energy:
            status = "filled" if self.container.get_level() > 0 else "empty"

            self.log_entry(
                "Energy use sailing {}".format(status),
                self.env.now,
                energy,
                self.geometry,
                self.ActivityID,
            )


class HasResource(SimpyObject):
    """HasProcessingLimit class

    Adds a limited Simpy resource which should be requested before the object is used for processing."""

    def __init__(self, nr_resources=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.resource = simpy.Resource(self.env, capacity=nr_resources)


class LogState(Enum):
    """LogState
    
    enumeration of all possible states of a Log object.
    Access the name using .name and the integer value using .value"""

    START = 1
    STOP = 2
    WAIT_START = 3
    WAIT_STOP = 4
    UNKNOWN = -1


class Log(SimpyObject):
    """Log class

    log: log message [format: 'start activity' or 'stop activity']
    t: timestamp
    value: a value can be logged as well
    geometry: value from locatable (lat, lon)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.log = {
            "Message": [],
            "Timestamp": [],
            "Value": [],
            "Geometry": [],
            "ActivityID": [],
            "ActivityState": [],
        }

    def log_entry(
        self, log, t, value, geometry_log, ActivityID, ActivityState=LogState.UNKNOWN
    ):
        """Log"""
        self.log["Message"].append(log)
        self.log["Timestamp"].append(datetime.datetime.fromtimestamp(t))
        self.log["Value"].append(value)
        self.log["Geometry"].append(geometry_log)
        self.log["ActivityID"].append(ActivityID)
        self.log["ActivityState"].append(ActivityState.name)

    def get_log_as_json(self):
        json = []
        for msg, t, value, geometry_log, act_state in zip(
            self.log["Message"],
            self.log["Timestamp"],
            self.log["Value"],
            self.log["Geometry"],
            self.log["ActivityState"],
        ):
            json.append(
                dict(
                    type="Feature",
                    geometry=shapely.geometry.mapping(geometry_log)
                    if geometry_log is not None
                    else "None",
                    properties=dict(
                        message=msg,
                        time=time.mktime(t.timetuple()),
                        value=value,
                        state=act_state,
                    ),
                )
            )
        return json


class LoadingFunction:
    """
    Create a loading function and add it a processor.
    This is a generic and easy to read function, you can create your own LoadingFunction class and add this as a mixin.

    loading_rate: the rate at which units are loaded per second
    load_manoeuvring: the time it takes to manoeuvring in minutes
    """

    def __init__(self, loading_rate, load_manoeuvring=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.loading_rate = loading_rate
        self.load_manoeuvring = load_manoeuvring

    def loading(self, origin, destination, amount, id_="default"):
        """
        Determine the duration based on an amount that is given as input with processing.
        The origin an destination are also part of the input, because other functions might be dependent on the location.
        """

        if not hasattr(self.loading_rate, "__call__"):
            return amount / self.loading_rate + self.load_manoeuvring * 60
        else:
            return (
                self.loading_rate(
                    destination.container.get_level(id_),
                    destination.container.get_level(id_) + amount,
                )
                + self.load_manoeuvring * 60
            )


class UnloadingFunction:
    """
    Create an unloading function and add it a processor.
    This is a generic and easy to read function, you can create your own LoadingFunction class and add this as a mixin.

    unloading_rate: the rate at which units are loaded per second
    unload_manoeuvring: the time it takes to manoeuvring in minutes
    """

    def __init__(self, unloading_rate, unload_manoeuvring=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.unloading_rate = unloading_rate
        self.unload_manoeuvring = unload_manoeuvring

    def unloading(self, origin, destination, amount, id_="default"):
        """
        Determine the duration based on an amount that is given as input with processing.
        The origin an destination are also part of the input, because other functions might be dependent on the location.
        """

        if not hasattr(self.unloading_rate, "__call__"):
            return amount / self.unloading_rate + self.unload_manoeuvring * 60
        else:
            return (
                self.unloading_rate(
                    origin.container.get_level(id_) + amount,
                    origin.container.get_level(id_),
                )
                + self.unload_manoeuvring * 60
            )


class LoadingSubcycle:
    """
    loading_subcycle: pandas dataframe with at least the columns EventName (str) and Duration (int or float in minutes)
    """

    def __init__(self, loading_subcycle, loading_subcycle_frequency, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.loading_subcycle = loading_subcycle
        self.loading_subcycle_frequency = loading_subcycle_frequency

        if type(self.loading_subcycle) != pd.core.frame.DataFrame:
            raise AssertionError("The subcycle table has to be a Pandas DataFrame")
        else:
            if "EventName" not in list(
                self.loading_subcycle.columns
            ) or "Duration" not in list(self.loading_subcycle.columns):
                raise AssertionError(
                    "The subcycle table should specify events and durations with the columnnames EventName and Duration respectively."
                )


class UnloadingSubcycle:
    """
    unloading_subcycle: pandas dataframe with at least the columns EventName (str) and Duration (int or float in minutes)
    """

    def __init__(
        self, unloading_subcycle, unloading_subcycle_frequency, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.unloading_subcycle = unloading_subcycle
        self.unloading_subcycle_frequency = unloading_subcycle_frequency

        if type(self.unloading_subcycle) != pd.core.frame.DataFrame:
            raise AssertionError("The subcycle table has to be a Pandas DataFrame")
        else:
            if "EventName" not in list(
                self.unloading_subcycle.columns
            ) or "Duration" not in list(self.unloading_subcycle.columns):
                raise AssertionError(
                    "The subcycle table should specify events and durations with the columnnames EventName and Duration respectively."
                )


class Processor(SimpyObject):
    """Processor class

    Adds the loading and unloading components and checks for possible downtime. 

    If the processor class is used to allow "loading" or "unloading" the mixins "LoadingFunction" and "UnloadingFunction" should be added as well. 
    If no functions are used a subcycle should be used, which is possible with the mixins "LoadingSubcycle" and "UnloadingSubcycle".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        # message = "{} has no (un)loading(_subcycle) attribute".format(self)
        # assert (
        #     hasattr(self, "loading")
        #     or hasattr(self, "unloading")
        #     or hasattr(self, "loading_subcycle")
        #     or hasattr(self, "unloading_subcycle")
        # ), message

        # Inherit the (un)loading functions
        if not hasattr(self, "loading"):
            self.loading = None
        if not hasattr(self, "unloading"):
            self.unloading = None

        # Inherit the subcycles
        if not hasattr(self, "loading_subcycle"):
            self.loading_subcycle = None
            self.loading_subcycle_frequency = None
        if not hasattr(self, "unloading_subcycle"):
            self.unloading_subcycle = None
            self.unloading_subcycle_frequency = None

    def determine_processor_amount(
        self,
        origins,
        destination,
        amount=None,
        id_="default",
        loader=None,
        unloader=None,
        filling=1,
    ):
        """ Determine the maximum amount that can be carried """

        # Determine the basic amount that should be transported
        all_amounts = {}
        all_amounts.update(
            {
                "origin." + origin.id: origin.container.get_level(id_)
                for origin in origins
            }
        )
        all_amounts[
            "destination." + destination.id
        ] = destination.container.get_capacity(id_) - destination.container.get_level(
            id_
        )
        print(all_amounts)

        origin_requested = 0
        destination_requested = 0

        for key in all_amounts.keys():
            if "origin." in key:
                origin_requested += all_amounts[key]
            else:
                destination_requested += all_amounts[key]

        amount_ = min(origin_requested, destination_requested)
        if amount != None:
            amount_ = min(amount_, amount)

        # If the mover has a function to optimize its load, check if the amount should be changed
        if not hasattr(destination, "check_optimal_filling"):
            return amount_, all_amounts

        else:
            amounts = [amount_]
            amounts.extend(
                [
                    destination.check_optimal_filling(
                        loader, unloader, origin, destination
                    )
                    for origin in origins
                ]
            )

            return min(amounts), all_amounts

    # noinspection PyUnresolvedReferences
    def process(
        self, origin, amount, destination, id_="default", rate=None, duration=None
    ):
        """Moves content from ship to the site or from the site to the ship to ensure that the ship's container reaches
        the desired level. Yields the time it takes to process."""

        # Before starting to process, check the following requirements
        # Make sure that both objects have storage
        assert isinstance(origin, HasContainer) and isinstance(
            destination, HasContainer
        )
        # Make sure that both objects allow processing
        assert isinstance(origin, HasResource) and isinstance(destination, HasResource)
        # Make sure that the processor (self), container and site can log the events
        assert (
            isinstance(self, Log)
            and isinstance(origin, Log)
            and isinstance(destination, Log)
        )
        # Make sure that the processor, origin and destination are all at the same location
        assert self.is_at(origin)
        assert destination.is_at(origin)

        # Define whether it is loading or unloading by the processor
        # no longer necessary
        # determine the base level of the origin
        current_level = origin.container.get_level(id_)

        # Loading the mover
        # if current_level < desired_level:
        #     amount = desired_level - current_level
        #     origin = site
        #     destination = mover
        #     rate = self.loading
        #     subcycle = self.loading_subcycle
        #     subcycle_frequency = self.loading_subcycle_frequency
        #     message = "loading"

        # # Unloading the mover
        # else:
        #     amount = current_level - desired_level
        #     origin = mover
        #     destination = site
        #     rate = self.unloading
        #     subcycle = self.unloading_subcycle
        #     subcycle_frequency = self.unloading_subcycle_frequency
        #     message = "unloading"

        message = f"transfer {id_} to {destination.name}"
        print(message)
        # Log the process for all parts
        for location in [origin, destination]:
            location.log_entry(
                log=message,
                t=location.env.now,
                value=amount,
                geometry_log=location.geometry,
                ActivityID=self.ActivityID,
                ActivityState=LogState.START,
            )

        # Single processing event
        # AW: I think these comments are not ok anymore
        if rate:
            print("processor process with rate")
            # Check whether the amount can me moved from the origin to the destination
            yield from self.check_possible_shift(
                origin, destination, amount, "get", id_
            )

            # Define the duration of the event
            duration = rate(origin, destination, amount)
            print("processing expected duration {duration}")
            # Check possible downtime
            yield from self.check_possible_downtime(
                origin, destination, duration, current_level + amount, amount, message
            )

            # Checkout single event
            self.log_entry(
                message,
                self.env.now,
                amount,
                self.geometry,
                self.ActivityID,
                LogState.START,
            )

            yield self.env.timeout(duration)

            # Put the amount in the destination
            yield from self.check_possible_shift(
                origin, destination, amount, "put", id_
            )

            # Add spill the location where processing is taking place
            self.addSpill(origin, destination, amount, duration)

            # Shift soil from container volumes
            self.shiftSoil(origin, destination, amount)

            # Compute the energy use
            self.computeEnergy(duration, origin, destination)

            self.log_entry(
                message,
                self.env.now,
                amount,
                self.geometry,
                self.ActivityID,
                LogState.STOP,
            )

        # Subcycle with processing events
        # AW: I think these comments are not ok anymore
        else:
            print("processor process without rate")
            yield from self.check_possible_shift(
                origin, destination, amount, "get", id_
            )

            print("after get")
            # Check possible downtime
            yield from self.check_possible_downtime(
                origin, destination, duration, current_level + amount, 1, message
            )
            print("after check_down time")

            # Checkout subcyle event
            self.log_entry(
                message,
                self.env.now,
                amount,
                self.geometry,
                self.ActivityID,
                LogState.START,
            )

            yield self.env.timeout(duration)

            # Put the amount in the destination
            yield from self.check_possible_shift(
                origin, destination, amount, "put", id_
            )
            print("after put")

            # Add spill the location where processing is taking place
            self.addSpill(origin, destination, amount, duration)

            # Shift soil from container volumes
            self.shiftSoil(origin, destination, amount)

            # Compute the energy use
            self.computeEnergy(duration, origin, destination)

            self.log_entry(
                message,
                self.env.now,
                amount,
                self.geometry,
                self.ActivityID,
                LogState.STOP,
            )

        # Log the process for all parts
        for location in [origin, destination]:
            location.log_entry(
                log=message,
                t=location.env.now,
                value=amount,
                geometry_log=location.geometry,
                ActivityID=self.ActivityID,
                ActivityState=LogState.STOP,
            )

        logger.debug("  process:        " + "%4.2f" % (duration / 3600) + " hrs")

    def check_possible_shift(
        self, origin, destination, amount, activity, id_="default"
    ):
        """ Check if all the material is available

        If the amount is not available in the origin or in the destination
        yield a put or get. Time will move forward until the amount can be 
        retrieved from the origin or placed into the destination.
        """

        if activity == "get":

            # Shift amounts in containers
            start_time = self.env.now
            print(f"origin store before get: {origin.container.items}")
            yield origin.container.get(amount, id_)
            print(f"origin store after get: {origin.container.items}")
            end_time = self.env.now

            # If the amount is not available in the origin, log waiting
            if start_time != end_time:
                self.log_entry(
                    log="waiting origin content",
                    t=start_time,
                    value=amount,
                    geometry_log=self.geometry,
                    ActivityID=self.ActivityID,
                    ActivityState=LogState.START,
                )
                self.log_entry(
                    log="waiting origin content",
                    t=end_time,
                    value=amount,
                    geometry_log=self.geometry,
                    ActivityID=self.ActivityID,
                    ActivityState=LogState.STOP,
                )

        elif activity == "put":

            # Shift amounts in containers
            start_time = self.env.now
            print(f"destination store before put: {destination.container.items}")
            yield destination.container.put(amount, id_=id_)
            print(f"destination store after put: {destination.container.items}")
            end_time = self.env.now

            # If the amount is cannot be put in the destination, log waiting
            if start_time != end_time:
                self.log_entry(
                    log="waiting destination content",
                    t=start_time,
                    value=amount,
                    geometry_log=self.geometry,
                    ActivityID=self.ActivityID,
                    ActivityState=LogState.START,
                )
                self.log_entry(
                    log="waiting destination content",
                    t=end_time,
                    value=amount,
                    geometry_log=self.geometry,
                    ActivityID=self.ActivityID,
                    ActivityState=LogState.STOP,
                )

    def check_possible_downtime(
        self, mover, site, duration, desired_level, amount, event_name
    ):
        # Activity can only start if environmental conditions allow it
        time = 0

        # Waiting event should be combined to check if all conditions allow starting
        while time != self.env.now:
            time = self.env.now

            # Check weather
            yield from self.checkWeather(
                processor=self, site=site, event_name=event_name
            )

            # Check tide
            yield from self.checkTide(
                mover=mover,
                site=site,
                desired_level=desired_level,
                amount=amount,
                duration=duration,
            )

            # Check spill
            yield from self.checkSpill(mover, site, amount)

    def computeEnergy(self, duration, origin, destination):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could consume energy
          2. Processor is also destination, origin could consume energy
          3. Processor is neither destination, nor origin, but both could consume energy
        """

        # If self == origin --> unloading
        if self == origin:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_unloading(duration)
                message = "Energy use unloading"
                self.log_entry(
                    message, self.env.now, energy, self.geometry, self.ActivityID
                )
            if isinstance(destination, EnergyUse):
                energy = destination.energy_use_loading(duration)
                message = "Energy use loading"
                destination.log_entry(
                    message, self.env.now, energy, destination.geometry, self.ActivityID
                )

        # If self == destination --> loading
        elif self == destination:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_loading(duration)
                message = "Energy use loading"
                self.log_entry(
                    message, self.env.now, energy, self.geometry, self.ActivityID
                )
            if isinstance(origin, EnergyUse):
                energy = origin.energy_use_unloading(duration)
                message = "Energy use unloading"
                origin.log_entry(
                    message, self.env.now, energy, origin.geometry, self.ActivityID
                )

        # If self != origin and self != destination --> processing
        else:
            if isinstance(self, EnergyUse):
                energy = self.energy_use_loading(duration)
                message = "Energy use loading"
                self.log_entry(
                    message, self.env.now, energy, self.geometry, self.ActivityID
                )
            if isinstance(origin, EnergyUse):
                energy = origin.energy_use_unloading(duration)
                message = "Energy use unloading"
                origin.log_entry(
                    message, self.env.now, energy, origin.geometry, self.ActivityID
                )
            if isinstance(destination, EnergyUse):
                energy = destination.energy_use_loading(duration)
                message = "Energy use loading"
                destination.log_entry(
                    message, self.env.now, energy, destination.geometry, self.ActivityID
                )

    def checkSpill(self, mover, site, amount):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could have spill requirements
          2. Processor is also destination, origin could have spill requirements
          3. Processor is neither destination, nor origin, but both could have spill requirements

        Result of this function is possible waiting, spill is added later on and does not depend on possible requirements
        """

        # If self == mover --> site is a placement location
        if self == mover:
            if (
                isinstance(site, HasSpillCondition)
                and isinstance(self, HasSoil)
                and isinstance(self, HasPlume)
                and 0 < self.container.get_level()
            ):
                density, fines = self.get_properties(amount)
                spill = self.sigma_d * density * fines * amount

                waiting = site.check_conditions(spill)

                if 0 < waiting:
                    self.log_entry(
                        "waiting for spill",
                        self.env.now,
                        0,
                        self.geometry,
                        self.ActivityID,
                        LogState.START,
                    )
                    yield self.env.timeout(waiting - self.env.now)
                    self.log_entry(
                        "waiting for spill",
                        self.env.now,
                        0,
                        self.geometry,
                        self.ActivityID,
                        LogState.STOP,
                    )

        # If self != origin and self != destination --> processing
        else:
            if (
                isinstance(site, HasSpillCondition)
                and isinstance(mover, HasSoil)
                and isinstance(self, HasPlume)
            ):
                density, fines = mover.get_properties(amount)
                spill = self.sigma_d * density * fines * amount

                waiting = site.check_conditions(spill)

                if 0 < waiting:
                    self.log_entry(
                        "waiting for spill",
                        self.env.now,
                        0,
                        self.geometry,
                        self.ActivityID,
                        LogState.START,
                    )
                    yield self.env.timeout(waiting - self.env.now)
                    self.log_entry(
                        "waiting for spill",
                        self.env.now,
                        0,
                        self.geometry,
                        self.ActivityID,
                        LogState.STOP,
                    )

    def checkTide(self, mover, site, desired_level, amount, duration):
        if hasattr(mover, "calc_depth_restrictions") and isinstance(
            site, HasAbstractWeather
        ):
            max_level = max(mover.container.get_level() + amount, desired_level)
            fill_degree = max_level / mover.container.get_capacity()
            yield from mover.check_depth_restriction(site, fill_degree, duration)

    def checkWeather(self, processor, site, event_name):
        if isinstance(processor, HasAbstractWorkabilityCriteria) and isinstance(
            site, HasAbstractWeather
        ):
            yield from processor.check_weather_restriction(site, event_name)

    def addSpill(self, origin, destination, amount, duration):
        """
        duration: duration of the activity in seconds
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)

        There are three options:
          1. Processor is also origin, destination could have spill requirements
          2. Processor is also destination, origin could have spill requirements
          3. Processor is neither destination, nor origin, but both could have spill requirements

        Result of this function is possible waiting, spill is added later on and does not depend on possible requirements
        """

        if isinstance(origin, HasSoil):
            density, fines = origin.get_properties(amount)

            # If self == origin --> destination is a placement location
            if self == origin:
                if isinstance(self, HasPlume) and isinstance(destination, HasSpill):
                    spill = destination.spillPlacement(self, self)

                    if 0 < spill and isinstance(destination, HasSpillCondition):
                        for condition in destination.SpillConditions["Spill limit"]:
                            condition.put(spill)

            # If self == destination --> origin is a retrieval location
            elif self == destination:
                if isinstance(self, HasPlume) and isinstance(origin, HasSpill):
                    spill = origin.spillDredging(
                        self, self, density, fines, amount, duration
                    )

                    if 0 < spill and isinstance(origin, HasSpillCondition):
                        for condition in origin.SpillConditions["Spill limit"]:
                            condition.put(spill)

            # If self != origin and self != destination --> processing
            else:
                if isinstance(self, HasPlume) and isinstance(destination, HasSpill):
                    spill = destination.spillPlacement(self, self)

                    if 0 < spill and isinstance(destination, HasSpillCondition):
                        for condition in destination.SpillConditions["Spill limit"]:
                            condition.put(spill)

                if isinstance(self, HasPlume) and isinstance(origin, HasSpill):
                    spill = origin.spillDredging(
                        self, self, density, fines, amount, duration
                    )

                    if 0 < spill and isinstance(origin, HasSpillCondition):
                        for condition in origin.SpillConditions["Spill limit"]:
                            condition.put(spill)

    def shiftSoil(self, origin, destination, amount):
        """
        origin: origin of the moved volume (the computed amount)
        destination: destination of the moved volume (the computed amount)
        amount: the volume of soil that is moved

        Can only occur if both the origin and the destination have soil objects (mix-ins)
        """

        if isinstance(origin, HasSoil) and isinstance(destination, HasSoil):
            soil = origin.get_soil(amount)
            destination.put_soil(soil)

        elif isinstance(origin, HasSoil):
            soil = origin.get_soil(amount)

        elif isinstance(destination, HasSoil):
            soil = SoilLayer(0, amount, "Unknown", 0, 0)
            destination.put_soil(soil)


class DictEncoder(json.JSONEncoder):
    """serialize a simpy openclsim object to json"""

    def default(self, o):
        result = {}
        for key, val in o.__dict__.items():
            if isinstance(val, simpy.Environment):
                continue
            if isinstance(val, EventsContainer) or isinstance(val, simpy.Container):
                result["capacity"] = val.get_capacity()
                result["level"] = val.get_level()
            elif isinstance(val, simpy.Resource):
                result["nr_resources"] = val.capacity
            else:
                result[key] = val

        return result


def serialize(obj):
    return json.dumps(obj, cls=DictEncoder)
