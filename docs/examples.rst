
Remaining issues:
=================

Handled issues:
---------------

-  [solved] distance between geometries is in degrees, we need it in
   meters to determine sailing durations
-  [solved] need to check resource requests closely to check why sharing
   ships isn't working yet
-  [solved] need to add resource requests to sites
-  [solved] need to add real time (plus a specific starting date)
-  [solved] need to add logging to Sites to lists volumes at different
   timesteps (this helps to animate on Google Earth)

Open issues:
------------

-  [open] need to add sensitivity to weather (see work Joris den Uijl)
-  [open] need to add soil characteristics and turbidity generation (see
   work Joris den Uijl)
-  [open] need to add routing via routing graph (Dijkstra algorithm)
-  [open] need to make case handling web based (quick setup & quick case
   comparison)
-  [open] need to collect the code in a package
-  [open] change processing so that it can handle rate\_in and rate\_out
   in stead of just rate

Create necessary classes
========================

.. code:: ipython3

    # package(s) related to time, space and id
    import datetime
    import platform
    
    # you need these dependencies (you can get these from anaconda)
    # package(s) related to the simulation
    import simpy
    
    # spatial libraries 
    import geojson
    import shapely.geometry
    from simplekml import Kml, Style
    
    # package(s) for data handling
    import numpy as np
    
    # digital twin package
    from  digital_twin.core import Identifiable, Site, TransportResource, TransportProcessingResource, ProcessingResource

Activities
----------

.. code:: ipython3

    class Installation(Identifiable):
        """The Installation Class forms a spefic class of activities with associated methods that can 
        initiate and suspend processes according to a number of specified conditions. This class deals 
        with transport and installation/placement of discrete and continuous objects.
        
        condition: expression that states when to initiate or to suspend activity
        origin: object with simpy Container from which to get (can be Site or Vessel)
        destination: object with simpy Container in which to put (can be Site or Vessel)
        loader: gets amount from 'origin' Container and puts it into 'mover' Container
        mover: moves amount in Container from 'origin' to 'destination'
        unloader: gets amount from 'mover' Container and puts it into 'destination' Container"""
    
        def __init__(self, 
                     condition,
                     origin, destination,  
                     loader, mover, unloader,
                     *args, **kwargs):
            super().__init__(*args, **kwargs)
            """Initialization"""
            
            self.condition = condition
            self.origin = origin
            self.destination = destination
            self.loader = loader
            self.mover = mover
            self.unloader = unloader
            
            self.standing_by_proc = env.process(
                self.standing_by(env, 
                                 condition,
                                 origin, destination,
                                 loader, mover, unloader))
            self.installation_proc = env.process(
                self.installation_process_control(env,
                                 condition,
                                 origin, destination,
                                 loader, mover, unloader))
            self.installation_reactivate = env.event()
    
        def standing_by(self, env, condition,
                              origin, destination,
                              loader, mover, unloader):
            """Standing by"""
            shown = False
    
            while not eval(condition):
                if not shown:
                    print('T=' + '{:06.2f}'.format(env.now) + ' ' + self.name + ' to ' + destination.name + ' suspended')
                    shown = True
                yield env.timeout(3600) # step 3600 time units ahead
    
            print('T=' + '{:06.2f}'.format(env.now) + ' ' + 'Condition: ' + condition + ' is satisfied')
    
            self.installation_reactivate.succeed()  # "reactivate"
            self.installation_reactivate = env.event()
     
        def installation_process_control(self, env, condition,
                                               origin, destination,
                                               loader, mover, unloader):
            """Installation process control"""  
            while not eval(condition):
                yield self.installation_reactivate
    
            print('T=' + '{:06.2f}'.format(env.now) + ' '+ self.name + ' to ' + destination.name + ' started')
            while eval(condition):
                yield from self.installation_process(env, condition,
                                                     origin, destination,
                                                     loader, mover, unloader)
    
        def installation_process(self, env, condition,
                                       origin, destination,
                                       loader, mover, unloader):
            """Installation process"""
            # estimate amount that should be transported
            amount = min(
                mover.container.capacity - mover.container.level,
                origin.container.level,
                origin.container.capacity - origin.total_requested,
                destination.container.capacity - destination.container.level,
                destination.container.capacity - destination.total_requested)
            
            if amount>0:
                # request access to the transport_resource
                origin.total_requested += amount
                destination.total_requested += amount
                if id(loader) == id(mover): 
                    # this is the case when a hopper is used
                    with mover.resource.request() as my_mover_turn:
                        yield my_mover_turn
    
                        # request access to the load_resource
                        mover.log_entry('loading start', self.env.now, mover.container.level)
                        yield from loader.execute_process(origin, mover, amount)
                        mover.log_entry('loading stop', self.env.now, mover.container.level)
    
                        print('Loaded:')
                        print('  from:           ' + origin.name + ' contains: ' + str(origin.container.level))
                        print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                        print('  to:             ' + destination.name + ' contains: ' + str(destination.container.level))
    
    
                        mover.log_entry('sailing full start', self.env.now, mover.container.level)
                        yield from mover.execute_move(origin, destination)
                        mover.log_entry('sailing full stop', self.env.now, mover.container.level)
    
                        # request access to the placement_resource
                        mover.log_entry('unloading start', self.env.now, mover.container.level)
                        yield from unloader.execute_process(mover, destination, amount)
                        mover.log_entry('unloading stop', self.env.now, mover.container.level)
    
                        print('Unloaded:')
                        print('  from:           ' + destination.name + ' contains: ' + str(destination.container.level))
                        print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                        print('  to:             ' + origin.name + ' contains: ' + str(origin.container.level))
    
                        mover.log_entry('sailing full start', self.env.now, mover.container.level)
                        yield from mover.execute_move(destination, origin)
                        mover.log_entry('sailing full stop', self.env.now, mover.container.level)
    
                        # once a mover is assigned to an Activity it completes a full cycle
                        mover.resource.release(my_mover_turn)
                else: 
                    # if not a hopper is used we have to handle resource requests differently
                    with mover.resource.request() as my_mover_turn:
                        yield my_mover_turn
    
                        # request access to the load_resource
                        with loader.resource.request() as my_load_resource_turn:
                            yield my_load_resource_turn
    
                            mover.log_entry('loading start', self.env.now, mover.container.level)
                            yield from loader.execute_process(origin, mover, amount)
                            mover.log_entry('loading stop', self.env.now, mover.container.level)
    
                            print('Loaded:')
                            print('  from:           ' + origin.name + ' contains: ' + str(origin.container.level))
                            print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                            print('  to:             ' + destination.name + ' contains: ' + str(destination.container.level))
    
                            loader.resource.release(my_load_resource_turn)
    
                        mover.log_entry('sailing full start', self.env.now, mover.container.level)
                        yield from mover.execute_move(origin, destination)
                        mover.log_entry('sailing full stop', self.env.now, mover.container.level)
    
                        # request access to the placement_resource
                        with unloader.resource.request() as my_unloader_turn:
                            yield my_unloader_turn
    
                            mover.log_entry('unloading start', self.env.now, mover.container.level)
                            yield from unloader.execute_process(mover, destination, amount)
                            mover.log_entry('unloading stop', self.env.now, mover.container.level)
    
                            print('Unloaded:')
                            print('  from:           ' + destination.name + ' contains: ' + str(destination.container.level))
                            print('  by:             ' + mover.name + ' contains: ' + str(mover.container.level))
                            print('  to:             ' + origin.name + ' contains: ' + str(origin.container.level))
    
                            unloader.resource.release(my_unloader_turn)
    
                        mover.log_entry('sailing full start', self.env.now, mover.container.level)
                        yield from mover.execute_move(destination, origin)
                        mover.log_entry('sailing full stop', self.env.now, mover.container.level)
    
                        # once a mover is assigned to an Activity it completes a full cycle
                        mover.resource.release(my_mover_turn)
            else:
                yield env.timeout(3600)
                

Start case
==========

.. code:: ipython3

    # *** Create a project environment
    env = simpy.Environment()
    start = env.now

.. code:: ipython3

    # simulation returns time in seconds with epoch as the reference
    env.epoch = datetime.datetime.now()

Define sites
------------

.. code:: ipython3

    Sites = []
    # *** Generate stock sites
    # - sites in database
    data_stock_01 = {"env": env,
                    "name": "Stock 01", "geometry": geojson.Point([5.019298185633251, 52.94239823421129]),
                    "capacity": 150000, "level": 150000}
    data_stock_02 = {"env": env,
                    "name": "Stock 02", "geometry": geojson.Point([5.271417603333632, 52.9638452897506]),
                    "capacity": 150000, "level": 150000}
    data_stock_03 = {"env": env,
                    "name": "Stock 03", "geometry": geojson.Point([5.919298185633251, 52.94239823421129]),
                    "capacity": 150000, "level": 150000}
    data_stock_04 = {"env": env,
                    "name": "Stock 04", "geometry": geojson.Point([5.919298185633251, 52.94239823421129]),
                    "capacity": 150000, "level": 150000}
    
    # - create site objects
    stock_01 = Site(**data_stock_01)
    Sites.append(stock_01)
    stock_02 = Site(**data_stock_02)
    Sites.append(stock_02)
    stock_03 = Site(**data_stock_03)
    Sites.append(stock_03)
    stock_04 = Site(**data_stock_04)
    Sites.append(stock_04)
    
    # *** Generate placement sites
    # - Clay layer
    layer_name = '_clay'
    capacity = 5000
    level = 0
    nums = 20
    start = [5.054676856441372,52.94042293840172] # Den Oever 
    stop = [5.294877712236641,53.06686424241725] # Kornwerderzand
    
    # - generate a 'nums' amount of sites between the selected start and stop points
    lats = np.linspace(start[0], stop[0], num=nums)
    lons = np.linspace(start[1], stop[1],  num=nums)
    
    # - option to create a range of sites between two points
    for i in range(nums):
        # - sites in database (nr indicates km's from Den Oever haven)
        data_site = {"env": env,
                    "name": "KP" + format(i,'02.0f') + layer_name, "geometry": geojson.Point([lats[i], lons[i]]),
                    "capacity": capacity, "level": level}
        
        # - create site objects
        vars()['Site_' + "KP" + format(i,'02.0f') + layer_name] = Site(**data_site)
        Sites.append(vars()['Site_' + "KP" + format(i,'02.0f') + layer_name])
    
    # - Sand layer
    layer_name = '_sand'
    capacity = 5000
    level = 0
    nums = 20
    start = [5.052051052879287,52.9421894472733] # Den Oever 
    stop = [5.292216781509101,53.06886359869087] # Kornwerderzand
    
    # - generate a 'nums' amount of sites between the selected start and stop points
    lats = np.linspace(start[0], stop[0], num=nums)
    lons = np.linspace(start[1], stop[1],  num=nums)
    
    # - option to create a range of sites between two points
    for i in range(nums):
        # - sites in database (nr indicates km's from Den Oever haven)
        data_site = {"env": env,
                    "name": "KP" + format(i,'02.0f') + layer_name, "geometry": geojson.Point([lats[i], lons[i]]),
                    "capacity": capacity, "level": level}
        
        # - create site objects
        vars()['Site_' + "KP" + format(i,'02.0f') + layer_name] = Site(**data_site)
        Sites.append(vars()['Site_' + "KP" + format(i,'02.0f') + layer_name])
    
    # - Armour layer
    layer_name = '_armour'
    capacity = 5000
    level = 0
    nums = 20
    start = [5.049510554598302,52.94393628899332] # Den Oever 
    stop = [5.289636346490858,53.07053144816584] # Kornwerderzand
    
    # - generate a 'nums' amount of sites between the selected start and stop points
    lats = np.linspace(start[0], stop[0], num=nums)
    lons = np.linspace(start[1], stop[1],  num=nums)
    
    # - option to create a range of sites between two points
    for i in range(nums):
        # - sites in database (nr indicates km's from Den Oever haven)
        data_site = {"env": env,
                    "name": "KP" + format(i,'02.0f') + layer_name, "geometry": geojson.Point([lats[i], lons[i]]),
                    "capacity": capacity, "level": level}
        
        # - create site objects
        vars()['Site_' + "KP" + format(i,'02.0f') + layer_name] = Site(**data_site)
        Sites.append(vars()['Site_' + "KP" + format(i,'02.0f') + layer_name])
    
    # - Levvel layer
    layer_name = '_levvel'
    capacity = 5000
    level = 0
    nums = 20
    start = [5.046556507026805,52.94579445406793] # Den Oever 
    stop = [5.286775240694118,53.07264015015531] # Kornwerderzand
    
    # - generate a 'nums' amount of sites between the selected start and stop points
    lats = np.linspace(start[0], stop[0], num=nums)
    lons = np.linspace(start[1], stop[1],  num=nums)
    
    # - option to create a range of sites between two points
    for i in range(nums):
        # - sites in database (nr indicates km's from Den Oever haven)
        data_site = {"env": env,
                    "name": "KP" + format(i,'02.0f') + layer_name, "geometry": geojson.Point([lats[i], lons[i]]),
                    "capacity": capacity, "level": level}
        
        # - create site objects
        vars()['Site_' + "KP" + format(i,'02.0f') + layer_name] = Site(**data_site)
        Sites.append(vars()['Site_' + "KP" + format(i,'02.0f') + layer_name])

Define equipment
----------------

.. code:: ipython3

    # *** Define fleet
    
    # sites in database (nr indicates km's from Den Oever haven)
    # - processing resources
    data_gantry_crane = {"env": env,
                    "name": "Gantry crane", "geometry": geojson.Point([52.94239823421129, 5.019298185633251]),
                    "rate": 0.10, "nr_resources": 1}
    data_installation_crane = {"env": env,
                    "name": "Installation crane", "geometry": geojson.Point([53.0229621352376,  5.197016484858931]),
                    "rate": 0.05, "nr_resources": 1}
    
    # - transport resources
    data_transport_barge_01 = {"env": env,
                    "name": "Transport barge 01", "geometry": geojson.Point([52.93917167503315, 5.070195628786471]),
                    "capacity": 1000, "level": 0, "nr_resources": 1, "v_empty":1.6, "v_full":1}
    data_transport_barge_02 = {"env": env,
                    "name": "Transport barge 02", "geometry": geojson.Point([52.93917167503315, 5.070195628786471]),
                    "capacity": 1000, "level": 0, "nr_resources": 1, "v_empty":1.6, "v_full":1}
    
    # - transport processing resources
    data_hopper = {"env": env,
                    "name": "Hopper", "geometry": geojson.Point([52.94239823421129, 5.019298185633251]),
                    "rate": 2, "nr_resources": 1, "capacity": 1000, "level": 0,  "nr_resources": 1, "v_empty":2, "v_full":1.5}
    
    # create site objects
    # - processing resources
    gantry_crane = ProcessingResource(**data_gantry_crane)
    installation_crane = ProcessingResource(**data_installation_crane)
    
    # - transport resources
    transport_barge_01 = TransportResource(**data_transport_barge_01)
    transport_barge_02 = TransportResource(**data_transport_barge_02)
    
    # - transport processing resources
    hopper = TransportProcessingResource(**data_hopper)

Define activities
-----------------

.. code:: ipython3

    # *** Define installation activities
    transport_barges=[]
    transport_barges.append(transport_barge_01)
    transport_barges.append(transport_barge_02)
    
    # Clay
    layer_name = '_clay'
    for i in range(nums):
        for transport_barge in transport_barges:
            # - sites in database (nr i indicates km's from Den Oever haven)
            if i==0:
                condition = "'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000'''"
                data_act = {"env": env,
                        "name": "Clay placement",
                        "origin": stock_01, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
            else:
                condition = "'''" + eval("'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000'''") + \
                            ' and ' + eval("'''Site_KP" + format(i-1,'02.0f') + layer_name + ".container.level==5000'''") + "'''"
                data_act = {"env": env,
                        "name": "Clay placement",
                        "origin": stock_01, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
    
            # - create site objects
            vars()['Act_' + format(i,'02.0f') + layer_name] = Installation(**data_act)
    
    # Sand
    layer_name = '_sand'
    previous_layer_name = '_clay'
    for i in range(nums):
        # - sites in database (nr i indicates km's from Den Oever haven)
        if i==0:
            condition =  "'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000" + \
                        ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
            data_act = {"env": env,
                    "name": "Sand placement",
                    "origin": stock_02, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                    "loader": hopper, "mover": hopper, "unloader": hopper,
                    "condition": eval(condition)}
        else:
            condition = "'''" + eval("'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000'''") + \
                        ' and ' + eval("'''Site_KP" + format(i-1,'02.0f') + layer_name + ".container.level==5000'''") + \
                        ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
            data_act = {"env": env,
                    "name": "Sand placement",
                    "origin": stock_02, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                    "loader": hopper, "mover": hopper, "unloader": hopper,
                    "condition": eval(condition)}
    
        # - create site objects
        vars()['Act_' + format(i,'02.0f') + layer_name] = Installation(**data_act)
    
    # Armour
    layer_name = '_armour'
    previous_layer_name = '_sand'
    for i in range(nums):
        for transport_barge in transport_barges:
            # - sites in database (nr i indicates km's from Den Oever haven)
            if i==0:
                condition =  "'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000" + \
                            ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
                data_act = {"env": env,
                        "name": "Armour placement",
                        "origin": stock_03, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
            else:
                condition = "'''" + eval("'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000'''") + \
                        ' and ' + eval("'''Site_KP" + format(i-1,'02.0f') + layer_name + ".container.level==5000'''") + \
                        ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
                data_act = {"env": env,
                        "name": "Armour placement",
                        "origin": stock_03, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
    
            # - create site objects
            vars()['Act_' + format(i,'02.0f') + layer_name] = Installation(**data_act)
    
    # Levvel
    layer_name = '_levvel'
    previous_layer_name = '_armour'
    for i in range(nums):
        for transport_barge in transport_barges:
        # - sites in database (nr i indicates km's from Den Oever haven)
            if i==0:
                condition =  "'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000" + \
                            ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
                data_act = {"env": env,
                        "name": "Block placement",
                        "origin": stock_04, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
            else:
                condition = "'''" + eval("'''Site_KP" + format(i,'02.0f') + layer_name + ".container.level<5000'''") + \
                        ' and ' + eval("'''Site_KP" + format(i-1,'02.0f') + layer_name + ".container.level==5000'''") + \
                        ' and ' + "Site_KP" + format(i,'02.0f') + previous_layer_name + ".container.level==5000'''"
                data_act = {"env": env,
                        "name": "Block placement",
                        "origin": stock_04, "destination": vars()['Site_' + "KP" + format(i,'02.0f') + layer_name],
                        "loader": gantry_crane, "mover": transport_barge, "unloader": installation_crane,
                        "condition": eval(condition)}
        
            # - create site objects
            vars()['Act_' + format(i,'02.0f') + layer_name] = Installation(**data_act)
                

Run simulation
--------------

.. code:: ipython3

    #*** Run the project
    env.run()


.. parsed-literal::

    T=000.00 Condition: Site_KP00_clay.container.level<5000 is satisfied
    T=000.00 Clay placement to KP00_clay started
    T=000.00 Condition: Site_KP00_clay.container.level<5000 is satisfied
    T=000.00 Clay placement to KP00_clay started
    T=000.00 Clay placement to KP01_clay suspended
    T=000.00 Clay placement to KP01_clay suspended
    T=000.00 Clay placement to KP02_clay suspended
    T=000.00 Clay placement to KP02_clay suspended
    T=000.00 Clay placement to KP03_clay suspended
    T=000.00 Clay placement to KP03_clay suspended
    T=000.00 Clay placement to KP04_clay suspended
    T=000.00 Clay placement to KP04_clay suspended
    T=000.00 Clay placement to KP05_clay suspended
    T=000.00 Clay placement to KP05_clay suspended
    T=000.00 Clay placement to KP06_clay suspended
    T=000.00 Clay placement to KP06_clay suspended
    T=000.00 Clay placement to KP07_clay suspended
    T=000.00 Clay placement to KP07_clay suspended
    T=000.00 Clay placement to KP08_clay suspended
    T=000.00 Clay placement to KP08_clay suspended
    T=000.00 Clay placement to KP09_clay suspended
    T=000.00 Clay placement to KP09_clay suspended
    T=000.00 Clay placement to KP10_clay suspended
    T=000.00 Clay placement to KP10_clay suspended
    T=000.00 Clay placement to KP11_clay suspended
    T=000.00 Clay placement to KP11_clay suspended
    T=000.00 Clay placement to KP12_clay suspended
    T=000.00 Clay placement to KP12_clay suspended
    T=000.00 Clay placement to KP13_clay suspended
    T=000.00 Clay placement to KP13_clay suspended
    T=000.00 Clay placement to KP14_clay suspended
    T=000.00 Clay placement to KP14_clay suspended
    T=000.00 Clay placement to KP15_clay suspended
    T=000.00 Clay placement to KP15_clay suspended
    T=000.00 Clay placement to KP16_clay suspended
    T=000.00 Clay placement to KP16_clay suspended
    T=000.00 Clay placement to KP17_clay suspended
    T=000.00 Clay placement to KP17_clay suspended
    T=000.00 Clay placement to KP18_clay suspended
    T=000.00 Clay placement to KP18_clay suspended
    T=000.00 Clay placement to KP19_clay suspended
    T=000.00 Clay placement to KP19_clay suspended
    T=000.00 Sand placement to KP00_sand suspended
    T=000.00 Sand placement to KP01_sand suspended
    T=000.00 Sand placement to KP02_sand suspended
    T=000.00 Sand placement to KP03_sand suspended
    T=000.00 Sand placement to KP04_sand suspended
    T=000.00 Sand placement to KP05_sand suspended
    T=000.00 Sand placement to KP06_sand suspended
    T=000.00 Sand placement to KP07_sand suspended
    T=000.00 Sand placement to KP08_sand suspended
    T=000.00 Sand placement to KP09_sand suspended
    T=000.00 Sand placement to KP10_sand suspended
    T=000.00 Sand placement to KP11_sand suspended
    T=000.00 Sand placement to KP12_sand suspended
    T=000.00 Sand placement to KP13_sand suspended
    T=000.00 Sand placement to KP14_sand suspended
    T=000.00 Sand placement to KP15_sand suspended
    T=000.00 Sand placement to KP16_sand suspended
    T=000.00 Sand placement to KP17_sand suspended
    T=000.00 Sand placement to KP18_sand suspended
    T=000.00 Sand placement to KP19_sand suspended
    T=000.00 Armour placement to KP00_armour suspended
    T=000.00 Armour placement to KP00_armour suspended
    T=000.00 Armour placement to KP01_armour suspended
    T=000.00 Armour placement to KP01_armour suspended
    T=000.00 Armour placement to KP02_armour suspended
    T=000.00 Armour placement to KP02_armour suspended
    T=000.00 Armour placement to KP03_armour suspended
    T=000.00 Armour placement to KP03_armour suspended
    T=000.00 Armour placement to KP04_armour suspended
    T=000.00 Armour placement to KP04_armour suspended
    T=000.00 Armour placement to KP05_armour suspended
    T=000.00 Armour placement to KP05_armour suspended
    T=000.00 Armour placement to KP06_armour suspended
    T=000.00 Armour placement to KP06_armour suspended
    T=000.00 Armour placement to KP07_armour suspended
    T=000.00 Armour placement to KP07_armour suspended
    T=000.00 Armour placement to KP08_armour suspended
    T=000.00 Armour placement to KP08_armour suspended
    T=000.00 Armour placement to KP09_armour suspended
    T=000.00 Armour placement to KP09_armour suspended
    T=000.00 Armour placement to KP10_armour suspended
    T=000.00 Armour placement to KP10_armour suspended
    T=000.00 Armour placement to KP11_armour suspended
    T=000.00 Armour placement to KP11_armour suspended
    T=000.00 Armour placement to KP12_armour suspended
    T=000.00 Armour placement to KP12_armour suspended
    T=000.00 Armour placement to KP13_armour suspended
    T=000.00 Armour placement to KP13_armour suspended
    T=000.00 Armour placement to KP14_armour suspended
    T=000.00 Armour placement to KP14_armour suspended
    T=000.00 Armour placement to KP15_armour suspended
    T=000.00 Armour placement to KP15_armour suspended
    T=000.00 Armour placement to KP16_armour suspended
    T=000.00 Armour placement to KP16_armour suspended
    T=000.00 Armour placement to KP17_armour suspended
    T=000.00 Armour placement to KP17_armour suspended
    T=000.00 Armour placement to KP18_armour suspended
    T=000.00 Armour placement to KP18_armour suspended
    T=000.00 Armour placement to KP19_armour suspended
    T=000.00 Armour placement to KP19_armour suspended
    T=000.00 Block placement to KP00_levvel suspended
    T=000.00 Block placement to KP00_levvel suspended
    T=000.00 Block placement to KP01_levvel suspended
    T=000.00 Block placement to KP01_levvel suspended
    T=000.00 Block placement to KP02_levvel suspended
    T=000.00 Block placement to KP02_levvel suspended
    T=000.00 Block placement to KP03_levvel suspended
    T=000.00 Block placement to KP03_levvel suspended
    T=000.00 Block placement to KP04_levvel suspended
    T=000.00 Block placement to KP04_levvel suspended
    T=000.00 Block placement to KP05_levvel suspended
    T=000.00 Block placement to KP05_levvel suspended
    T=000.00 Block placement to KP06_levvel suspended
    T=000.00 Block placement to KP06_levvel suspended
    T=000.00 Block placement to KP07_levvel suspended
    T=000.00 Block placement to KP07_levvel suspended
    T=000.00 Block placement to KP08_levvel suspended
    T=000.00 Block placement to KP08_levvel suspended
    T=000.00 Block placement to KP09_levvel suspended
    T=000.00 Block placement to KP09_levvel suspended
    T=000.00 Block placement to KP10_levvel suspended
    T=000.00 Block placement to KP10_levvel suspended
    T=000.00 Block placement to KP11_levvel suspended
    T=000.00 Block placement to KP11_levvel suspended
    T=000.00 Block placement to KP12_levvel suspended
    T=000.00 Block placement to KP12_levvel suspended
    T=000.00 Block placement to KP13_levvel suspended
    T=000.00 Block placement to KP13_levvel suspended
    T=000.00 Block placement to KP14_levvel suspended
    T=000.00 Block placement to KP14_levvel suspended
    T=000.00 Block placement to KP15_levvel suspended
    T=000.00 Block placement to KP15_levvel suspended
    T=000.00 Block placement to KP16_levvel suspended
    T=000.00 Block placement to KP16_levvel suspended
    T=000.00 Block placement to KP17_levvel suspended
    T=000.00 Block placement to KP17_levvel suspended
    T=000.00 Block placement to KP18_levvel suspended
    T=000.00 Block placement to KP18_levvel suspended
    T=000.00 Block placement to KP19_levvel suspended
    T=000.00 Block placement to KP19_levvel suspended
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 149000
      by:             Transport barge 01 contains: 1000
      to:             KP00_clay contains: 0
      distance full:  2388.58 m
      sailing full:   1.00 m/s
      duration:       0.66 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 148000
      by:             Transport barge 02 contains: 1000
      to:             KP00_clay contains: 1000
      distance full:  2388.58 m
      sailing full:   1.00 m/s
      duration:       0.66 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 148000
      distance empty: 2388.58 m
      sailing empty:  1.60 m/s
      duration:       0.41 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 147000
      by:             Transport barge 01 contains: 1000
      to:             KP00_clay contains: 2000
      distance full:  2388.58 m
      sailing full:   1.00 m/s
      duration:       0.66 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 147000
      distance empty: 2388.58 m
      sailing empty:  1.60 m/s
      duration:       0.41 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 146000
      by:             Transport barge 02 contains: 1000
      to:             KP00_clay contains: 3000
      distance full:  2388.58 m
      sailing full:   1.00 m/s
      duration:       0.66 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 146000
      distance empty: 2388.58 m
      sailing empty:  1.60 m/s
      duration:       0.41 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 145000
      by:             Transport barge 01 contains: 1000
      to:             KP00_clay contains: 4000
      distance full:  2388.58 m
      sailing full:   1.00 m/s
      duration:       0.66 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 145000
    T=93600.00 Condition: Site_KP01_clay.container.level<5000 and Site_KP00_clay.container.level==5000 is satisfied
    T=93600.00 Condition: Site_KP01_clay.container.level<5000 and Site_KP00_clay.container.level==5000 is satisfied
    T=93600.00 Condition: Site_KP00_sand.container.level<5000 and Site_KP00_clay.container.level==5000 is satisfied
    T=93600.00 Clay placement to KP01_clay started
    T=93600.00 Clay placement to KP01_clay started
    T=93600.00 Sand placement to KP00_sand started
      distance empty: 2388.58 m
      sailing empty:  1.60 m/s
      duration:       0.41 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 149000
      by:             Hopper contains: 1000
      to:             KP00_sand contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 144000
      by:             Transport barge 02 contains: 1000
      to:             KP01_clay contains: 0
      distance full:  14939.31 m
      sailing full:   1.50 m/s
      duration:       2.77 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP00_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 149000
      distance full:  3269.83 m
      sailing full:   1.00 m/s
      duration:       0.91 hrs
      distance empty: 14939.31 m
      sailing empty:  2.00 m/s
      duration:       2.07 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 144000
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 148000
      by:             Hopper contains: 1000
      to:             KP00_sand contains: 1000
      distance empty: 2388.58 m
      sailing empty:  1.60 m/s
      duration:       0.41 hrs
      distance full:  14939.31 m
      sailing full:   1.50 m/s
      duration:       2.77 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP00_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 148000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 143000
      by:             Transport barge 01 contains: 1000
      to:             KP01_clay contains: 1000
      distance full:  3269.83 m
      sailing full:   1.00 m/s
      duration:       0.91 hrs
      distance empty: 14939.31 m
      sailing empty:  2.00 m/s
      duration:       2.07 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 147000
      by:             Hopper contains: 1000
      to:             KP00_sand contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 143000
      distance empty: 3269.83 m
      sailing empty:  1.60 m/s
      duration:       0.57 hrs
      distance full:  14939.31 m
      sailing full:   1.50 m/s
      duration:       2.77 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP00_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 147000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 142000
      by:             Transport barge 02 contains: 1000
      to:             KP01_clay contains: 2000
      distance full:  3269.83 m
      sailing full:   1.00 m/s
      duration:       0.91 hrs
      distance empty: 14939.31 m
      sailing empty:  2.00 m/s
      duration:       2.07 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 146000
      by:             Hopper contains: 1000
      to:             KP00_sand contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 142000
      distance empty: 3269.83 m
      sailing empty:  1.60 m/s
      duration:       0.57 hrs
      distance full:  14939.31 m
      sailing full:   1.50 m/s
      duration:       2.77 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP00_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 146000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 141000
      by:             Transport barge 01 contains: 1000
      to:             KP01_clay contains: 3000
      distance empty: 14939.31 m
      sailing empty:  2.00 m/s
      duration:       2.07 hrs
      distance full:  3269.83 m
      sailing full:   1.00 m/s
      duration:       0.91 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 145000
      by:             Hopper contains: 1000
      to:             KP00_sand contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 141000
      distance empty: 3269.83 m
      sailing empty:  1.60 m/s
      duration:       0.57 hrs
      distance full:  14939.31 m
      sailing full:   1.50 m/s
      duration:       2.77 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP00_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 145000
    T=180000.00 Condition: Site_KP00_armour.container.level<5000 and Site_KP00_sand.container.level==5000 is satisfied
    T=180000.00 Condition: Site_KP00_armour.container.level<5000 and Site_KP00_sand.container.level==5000 is satisfied
    T=180000.00 Armour placement to KP00_armour started
    T=180000.00 Armour placement to KP00_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 140000
      by:             Transport barge 02 contains: 1000
      to:             KP01_clay contains: 4000
      distance empty: 14939.31 m
      sailing empty:  2.00 m/s
      duration:       2.07 hrs
      distance full:  3269.83 m
      sailing full:   1.00 m/s
      duration:       0.91 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP01_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 140000
    T=194400.00 Condition: Site_KP02_clay.container.level<5000 and Site_KP01_clay.container.level==5000 is satisfied
    T=194400.00 Condition: Site_KP02_clay.container.level<5000 and Site_KP01_clay.container.level==5000 is satisfied
    T=194400.00 Condition: Site_KP01_sand.container.level<5000 and Site_KP00_sand.container.level==5000 and Site_KP01_clay.container.level==5000 is satisfied
    T=194400.00 Clay placement to KP02_clay started
    T=194400.00 Clay placement to KP02_clay started
    T=194400.00 Sand placement to KP01_sand started
      distance empty: 3269.83 m
      sailing empty:  1.60 m/s
      duration:       0.57 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 144000
      by:             Hopper contains: 1000
      to:             KP01_sand contains: 0
      distance full:  13992.79 m
      sailing full:   1.50 m/s
      duration:       2.59 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 149000
      by:             Transport barge 01 contains: 1000
      to:             KP00_armour contains: 0
      process:        0.14 hrs
    Unloaded:
      from:           KP01_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 144000
      distance empty: 13992.79 m
      sailing empty:  2.00 m/s
      duration:       1.94 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 143000
      by:             Hopper contains: 1000
      to:             KP01_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 140000
      distance empty: 3269.83 m
      sailing empty:  1.60 m/s
      duration:       0.57 hrs
      distance full:  13992.79 m
      sailing full:   1.50 m/s
      duration:       2.59 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP01_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 143000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 148000
      by:             Transport barge 02 contains: 1000
      to:             KP00_armour contains: 0
      distance empty: 13992.79 m
      sailing empty:  2.00 m/s
      duration:       1.94 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 142000
      by:             Hopper contains: 1000
      to:             KP01_sand contains: 2000
      distance full:  13992.79 m
      sailing full:   1.50 m/s
      duration:       2.59 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP01_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 142000
      distance empty: 13992.79 m
      sailing empty:  2.00 m/s
      duration:       1.94 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 141000
      by:             Hopper contains: 1000
      to:             KP01_sand contains: 3000
      distance full:  13992.79 m
      sailing full:   1.50 m/s
      duration:       2.59 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP01_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 141000
      distance full:  58471.67 m
      sailing full:   1.00 m/s
      duration:       16.24 hrs
      distance empty: 13992.79 m
      sailing empty:  2.00 m/s
      duration:       1.94 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 140000
      by:             Hopper contains: 1000
      to:             KP01_sand contains: 4000
      distance full:  13992.79 m
      sailing full:   1.50 m/s
      duration:       2.59 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP01_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 140000
      distance empty: 13992.79 m
      sailing empty:  2.00 m/s
      duration:       1.94 hrs
      distance full:  58471.67 m
      sailing full:   1.00 m/s
      duration:       16.24 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 148000
      process:        5.56 hrs
    Unloaded:
      from:           KP00_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 148000
      distance empty: 58471.67 m
      sailing empty:  1.60 m/s
      duration:       10.15 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 139000
      by:             Transport barge 01 contains: 1000
      to:             KP02_clay contains: 0
      distance full:  4268.26 m
      sailing full:   1.00 m/s
      duration:       1.19 hrs
      distance empty: 58471.67 m
      sailing empty:  1.60 m/s
      duration:       10.15 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 138000
      by:             Transport barge 02 contains: 1000
      to:             KP02_clay contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 138000
      distance full:  4268.26 m
      sailing full:   1.00 m/s
      duration:       1.19 hrs
      distance empty: 4268.26 m
      sailing empty:  1.60 m/s
      duration:       0.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 147000
      by:             Transport barge 01 contains: 1000
      to:             KP00_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 138000
      distance empty: 4268.26 m
      sailing empty:  1.60 m/s
      duration:       0.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 146000
      by:             Transport barge 02 contains: 1000
      to:             KP00_armour contains: 2000
      distance full:  58471.67 m
      sailing full:   1.00 m/s
      duration:       16.24 hrs
      distance full:  58471.67 m
      sailing full:   1.00 m/s
      duration:       16.24 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 146000
      process:        5.56 hrs
    Unloaded:
      from:           KP00_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 146000
      distance empty: 58471.67 m
      sailing empty:  1.60 m/s
      duration:       10.15 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 137000
      by:             Transport barge 01 contains: 1000
      to:             KP02_clay contains: 2000
      distance full:  4268.26 m
      sailing full:   1.00 m/s
      duration:       1.19 hrs
      distance empty: 58471.67 m
      sailing empty:  1.60 m/s
      duration:       10.15 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 136000
      by:             Transport barge 02 contains: 1000
      to:             KP02_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 136000
      distance full:  4268.26 m
      sailing full:   1.00 m/s
      duration:       1.19 hrs
      distance empty: 4268.26 m
      sailing empty:  1.60 m/s
      duration:       0.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 145000
      by:             Transport barge 01 contains: 1000
      to:             KP00_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 136000
      distance empty: 4268.26 m
      sailing empty:  1.60 m/s
      duration:       0.74 hrs
      distance full:  58471.67 m
      sailing full:   1.00 m/s
      duration:       16.24 hrs
    T=590400.00 Condition: Site_KP01_armour.container.level<5000 and Site_KP00_armour.container.level==5000 and Site_KP01_sand.container.level==5000 is satisfied
    T=590400.00 Condition: Site_KP01_armour.container.level<5000 and Site_KP00_armour.container.level==5000 and Site_KP01_sand.container.level==5000 is satisfied
    T=590400.00 Condition: Site_KP00_levvel.container.level<5000 and Site_KP00_armour.container.level==5000 is satisfied
    T=590400.00 Condition: Site_KP00_levvel.container.level<5000 and Site_KP00_armour.container.level==5000 is satisfied
    T=590400.00 Armour placement to KP01_armour started
    T=590400.00 Armour placement to KP01_armour started
    T=590400.00 Block placement to KP00_levvel started
    T=590400.00 Block placement to KP00_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 144000
      by:             Transport barge 02 contains: 1000
      to:             KP01_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP00_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 144000
      distance empty: 58471.67 m
      sailing empty:  1.60 m/s
      duration:       10.15 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 135000
      by:             Transport barge 01 contains: 1000
      to:             KP02_clay contains: 4000
      distance full:  4268.26 m
      sailing full:   1.00 m/s
      duration:       1.19 hrs
      distance full:  57624.63 m
      sailing full:   1.00 m/s
      duration:       16.01 hrs
    T=658800.00 Condition: Site_KP03_clay.container.level<5000 and Site_KP02_clay.container.level==5000 is satisfied
    T=658800.00 Condition: Site_KP03_clay.container.level<5000 and Site_KP02_clay.container.level==5000 is satisfied
    T=658800.00 Condition: Site_KP02_sand.container.level<5000 and Site_KP01_sand.container.level==5000 and Site_KP02_clay.container.level==5000 is satisfied
    T=658800.00 Clay placement to KP03_clay started
    T=658800.00 Clay placement to KP03_clay started
    T=658800.00 Sand placement to KP02_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 139000
      by:             Hopper contains: 1000
      to:             KP02_sand contains: 0
      distance full:  13075.36 m
      sailing full:   1.50 m/s
      duration:       2.42 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP02_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 139000
      distance empty: 13075.36 m
      sailing empty:  2.00 m/s
      duration:       1.82 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 138000
      by:             Hopper contains: 1000
      to:             KP02_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 135000
      distance empty: 4268.26 m
      sailing empty:  1.60 m/s
      duration:       0.74 hrs
      distance full:  13075.36 m
      sailing full:   1.50 m/s
      duration:       2.42 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP02_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 138000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 143000
      by:             Transport barge 01 contains: 1000
      to:             KP01_armour contains: 1000
      distance empty: 13075.36 m
      sailing empty:  2.00 m/s
      duration:       1.82 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 137000
      by:             Hopper contains: 1000
      to:             KP02_sand contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 143000
      distance full:  13075.36 m
      sailing full:   1.50 m/s
      duration:       2.42 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP02_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 137000
      distance empty: 13075.36 m
      sailing empty:  2.00 m/s
      duration:       1.82 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 136000
      by:             Hopper contains: 1000
      to:             KP02_sand contains: 3000
      distance full:  13075.36 m
      sailing full:   1.50 m/s
      duration:       2.42 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP02_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 136000
      distance empty: 13075.36 m
      sailing empty:  2.00 m/s
      duration:       1.82 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 135000
      by:             Hopper contains: 1000
      to:             KP02_sand contains: 4000
      distance full:  13075.36 m
      sailing full:   1.50 m/s
      duration:       2.42 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP02_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 135000
      distance empty: 57624.63 m
      sailing empty:  1.60 m/s
      duration:       10.00 hrs
      distance empty: 13075.36 m
      sailing empty:  2.00 m/s
      duration:       1.82 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 149000
      by:             Transport barge 02 contains: 1000
      to:             KP00_levvel contains: 0
      distance full:  57624.63 m
      sailing full:   1.00 m/s
      duration:       16.01 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP01_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 143000
      distance full:  58669.97 m
      sailing full:   1.00 m/s
      duration:       16.30 hrs
      distance empty: 57624.63 m
      sailing empty:  1.60 m/s
      duration:       10.00 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 148000
      by:             Transport barge 01 contains: 1000
      to:             KP00_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP00_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 148000
      distance empty: 58669.97 m
      sailing empty:  1.60 m/s
      duration:       10.19 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 134000
      by:             Transport barge 02 contains: 1000
      to:             KP03_clay contains: 0
      distance full:  58669.97 m
      sailing full:   1.00 m/s
      duration:       16.30 hrs
      distance full:  5318.21 m
      sailing full:   1.00 m/s
      duration:       1.48 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 148000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 134000
      distance empty: 5318.21 m
      sailing empty:  1.60 m/s
      duration:       0.92 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 142000
      by:             Transport barge 02 contains: 1000
      to:             KP01_armour contains: 2000
      distance empty: 58669.97 m
      sailing empty:  1.60 m/s
      duration:       10.19 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 133000
      by:             Transport barge 01 contains: 1000
      to:             KP03_clay contains: 1000
      distance full:  5318.21 m
      sailing full:   1.00 m/s
      duration:       1.48 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP03_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 133000
      distance empty: 5318.21 m
      sailing empty:  1.60 m/s
      duration:       0.92 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 141000
      by:             Transport barge 01 contains: 1000
      to:             KP01_armour contains: 2000
      distance full:  57624.63 m
      sailing full:   1.00 m/s
      duration:       16.01 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP01_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 141000
      distance full:  57624.63 m
      sailing full:   1.00 m/s
      duration:       16.01 hrs
      distance empty: 57624.63 m
      sailing empty:  1.60 m/s
      duration:       10.00 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 147000
      by:             Transport barge 02 contains: 1000
      to:             KP00_levvel contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 141000
      distance empty: 57624.63 m
      sailing empty:  1.60 m/s
      duration:       10.00 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 146000
      by:             Transport barge 01 contains: 1000
      to:             KP00_levvel contains: 2000
      distance full:  58669.97 m
      sailing full:   1.00 m/s
      duration:       16.30 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP00_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 146000
      distance full:  58669.97 m
      sailing full:   1.00 m/s
      duration:       16.30 hrs
      distance empty: 58669.97 m
      sailing empty:  1.60 m/s
      duration:       10.19 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 132000
      by:             Transport barge 02 contains: 1000
      to:             KP03_clay contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP00_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 146000
      distance full:  5318.21 m
      sailing full:   1.00 m/s
      duration:       1.48 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP03_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 132000
      distance empty: 5318.21 m
      sailing empty:  1.60 m/s
      duration:       0.92 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 140000
      by:             Transport barge 02 contains: 1000
      to:             KP01_armour contains: 4000
      distance empty: 58669.97 m
      sailing empty:  1.60 m/s
      duration:       10.19 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 131000
      by:             Transport barge 01 contains: 1000
      to:             KP03_clay contains: 3000
      distance full:  5318.21 m
      sailing full:   1.00 m/s
      duration:       1.48 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP03_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 131000
      distance empty: 5318.21 m
      sailing empty:  1.60 m/s
      duration:       0.92 hrs
      distance full:  57624.63 m
      sailing full:   1.00 m/s
      duration:       16.01 hrs
    T=1274400.00 Condition: Site_KP02_armour.container.level<5000 and Site_KP01_armour.container.level==5000 and Site_KP02_sand.container.level==5000 is satisfied
    T=1274400.00 Condition: Site_KP02_armour.container.level<5000 and Site_KP01_armour.container.level==5000 and Site_KP02_sand.container.level==5000 is satisfied
    T=1274400.00 Armour placement to KP02_armour started
    T=1274400.00 Armour placement to KP02_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 139000
      by:             Transport barge 01 contains: 1000
      to:             KP02_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP01_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 139000
      distance empty: 57624.63 m
      sailing empty:  1.60 m/s
      duration:       10.00 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 145000
      by:             Transport barge 02 contains: 1000
      to:             KP00_levvel contains: 4000
      distance full:  56787.61 m
      sailing full:   1.00 m/s
      duration:       15.77 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 139000
      distance full:  58669.97 m
      sailing full:   1.00 m/s
      duration:       16.30 hrs
      distance empty: 56787.61 m
      sailing empty:  1.60 m/s
      duration:       9.86 hrs
    T=1396800.00 Condition: Site_KP01_levvel.container.level<5000 and Site_KP00_levvel.container.level==5000 and Site_KP01_armour.container.level==5000 is satisfied
    T=1396800.00 Condition: Site_KP01_levvel.container.level<5000 and Site_KP00_levvel.container.level==5000 and Site_KP01_armour.container.level==5000 is satisfied
    T=1396800.00 Block placement to KP01_levvel started
    T=1396800.00 Block placement to KP01_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 138000
      by:             Transport barge 01 contains: 1000
      to:             KP02_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP00_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 145000
      distance empty: 58669.97 m
      sailing empty:  1.60 m/s
      duration:       10.19 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 130000
      by:             Transport barge 02 contains: 1000
      to:             KP03_clay contains: 4000
      distance full:  56787.61 m
      sailing full:   1.00 m/s
      duration:       15.77 hrs
      distance full:  5318.21 m
      sailing full:   1.00 m/s
      duration:       1.48 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 138000
    T=1486800.00 Condition: Site_KP04_clay.container.level<5000 and Site_KP03_clay.container.level==5000 is satisfied
    T=1486800.00 Condition: Site_KP04_clay.container.level<5000 and Site_KP03_clay.container.level==5000 is satisfied
    T=1486800.00 Condition: Site_KP03_sand.container.level<5000 and Site_KP02_sand.container.level==5000 and Site_KP03_clay.container.level==5000 is satisfied
    T=1486800.00 Clay placement to KP04_clay started
    T=1486800.00 Clay placement to KP04_clay started
    T=1486800.00 Sand placement to KP03_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 134000
      by:             Hopper contains: 1000
      to:             KP03_sand contains: 0
      distance full:  12193.55 m
      sailing full:   1.50 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP03_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 134000
      distance empty: 12193.55 m
      sailing empty:  2.00 m/s
      duration:       1.69 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 133000
      by:             Hopper contains: 1000
      to:             KP03_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 130000
      distance empty: 5318.21 m
      sailing empty:  1.60 m/s
      duration:       0.92 hrs
      distance full:  12193.55 m
      sailing full:   1.50 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP03_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 133000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 137000
      by:             Transport barge 02 contains: 1000
      to:             KP02_armour contains: 2000
      distance empty: 12193.55 m
      sailing empty:  2.00 m/s
      duration:       1.69 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 132000
      by:             Hopper contains: 1000
      to:             KP03_sand contains: 2000
      distance empty: 56787.61 m
      sailing empty:  1.60 m/s
      duration:       9.86 hrs
      distance full:  12193.55 m
      sailing full:   1.50 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP03_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 132000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 144000
      by:             Transport barge 01 contains: 1000
      to:             KP01_levvel contains: 0
      distance empty: 12193.55 m
      sailing empty:  2.00 m/s
      duration:       1.69 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 131000
      by:             Hopper contains: 1000
      to:             KP03_sand contains: 3000
      distance full:  12193.55 m
      sailing full:   1.50 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP03_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 131000
      distance empty: 12193.55 m
      sailing empty:  2.00 m/s
      duration:       1.69 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 130000
      by:             Hopper contains: 1000
      to:             KP03_sand contains: 4000
      distance full:  12193.55 m
      sailing full:   1.50 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP03_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 130000
      distance empty: 12193.55 m
      sailing empty:  2.00 m/s
      duration:       1.69 hrs
      distance full:  56787.61 m
      sailing full:   1.00 m/s
      duration:       15.77 hrs
      distance full:  57825.26 m
      sailing full:   1.00 m/s
      duration:       16.06 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 137000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 144000
      distance empty: 56787.61 m
      sailing empty:  1.60 m/s
      duration:       9.86 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 143000
      by:             Transport barge 02 contains: 1000
      to:             KP01_levvel contains: 1000
      distance empty: 57825.26 m
      sailing empty:  1.60 m/s
      duration:       10.04 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 129000
      by:             Transport barge 01 contains: 1000
      to:             KP04_clay contains: 0
      distance full:  6394.29 m
      sailing full:   1.00 m/s
      duration:       1.78 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 129000
      distance empty: 6394.29 m
      sailing empty:  1.60 m/s
      duration:       1.11 hrs
      distance full:  57825.26 m
      sailing full:   1.00 m/s
      duration:       16.06 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 136000
      by:             Transport barge 01 contains: 1000
      to:             KP02_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 143000
      distance empty: 57825.26 m
      sailing empty:  1.60 m/s
      duration:       10.04 hrs
      distance full:  56787.61 m
      sailing full:   1.00 m/s
      duration:       15.77 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 128000
      by:             Transport barge 02 contains: 1000
      to:             KP04_clay contains: 1000
      distance full:  6394.29 m
      sailing full:   1.00 m/s
      duration:       1.78 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 136000
      process:        5.56 hrs
    Unloaded:
      from:           KP04_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 128000
      distance empty: 6394.29 m
      sailing empty:  1.60 m/s
      duration:       1.11 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 135000
      by:             Transport barge 02 contains: 1000
      to:             KP02_armour contains: 4000
      distance empty: 56787.61 m
      sailing empty:  1.60 m/s
      duration:       9.86 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 142000
      by:             Transport barge 01 contains: 1000
      to:             KP01_levvel contains: 2000
      distance full:  56787.61 m
      sailing full:   1.00 m/s
      duration:       15.77 hrs
    T=1868400.00 Condition: Site_KP03_armour.container.level<5000 and Site_KP02_armour.container.level==5000 and Site_KP03_sand.container.level==5000 is satisfied
    T=1868400.00 Condition: Site_KP03_armour.container.level<5000 and Site_KP02_armour.container.level==5000 and Site_KP03_sand.container.level==5000 is satisfied
    T=1868400.00 Armour placement to KP03_armour started
    T=1868400.00 Armour placement to KP03_armour started
      distance full:  57825.26 m
      sailing full:   1.00 m/s
      duration:       16.06 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 135000
      process:        5.56 hrs
    Unloaded:
      from:           KP01_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 142000
      distance empty: 56787.61 m
      sailing empty:  1.60 m/s
      duration:       9.86 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 141000
      by:             Transport barge 02 contains: 1000
      to:             KP01_levvel contains: 3000
      distance empty: 57825.26 m
      sailing empty:  1.60 m/s
      duration:       10.04 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 127000
      by:             Transport barge 01 contains: 1000
      to:             KP04_clay contains: 2000
      distance full:  6394.29 m
      sailing full:   1.00 m/s
      duration:       1.78 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 127000
      distance empty: 6394.29 m
      sailing empty:  1.60 m/s
      duration:       1.11 hrs
      distance full:  57825.26 m
      sailing full:   1.00 m/s
      duration:       16.06 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 134000
      by:             Transport barge 01 contains: 1000
      to:             KP03_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP01_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 141000
      distance empty: 57825.26 m
      sailing empty:  1.60 m/s
      duration:       10.04 hrs
      distance full:  55961.05 m
      sailing full:   1.00 m/s
      duration:       15.54 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 126000
      by:             Transport barge 02 contains: 1000
      to:             KP04_clay contains: 3000
      distance full:  6394.29 m
      sailing full:   1.00 m/s
      duration:       1.78 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP03_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 134000
      process:        5.56 hrs
    Unloaded:
      from:           KP04_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 126000
      distance empty: 6394.29 m
      sailing empty:  1.60 m/s
      duration:       1.11 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 133000
      by:             Transport barge 02 contains: 1000
      to:             KP03_armour contains: 1000
      distance empty: 55961.05 m
      sailing empty:  1.60 m/s
      duration:       9.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 140000
      by:             Transport barge 01 contains: 1000
      to:             KP01_levvel contains: 4000
      distance full:  55961.05 m
      sailing full:   1.00 m/s
      duration:       15.54 hrs
      distance full:  57825.26 m
      sailing full:   1.00 m/s
      duration:       16.06 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP03_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 133000
    T=2181600.00 Condition: Site_KP02_levvel.container.level<5000 and Site_KP01_levvel.container.level==5000 and Site_KP02_armour.container.level==5000 is satisfied
    T=2181600.00 Condition: Site_KP02_levvel.container.level<5000 and Site_KP01_levvel.container.level==5000 and Site_KP02_armour.container.level==5000 is satisfied
    T=2181600.00 Block placement to KP02_levvel started
    T=2181600.00 Block placement to KP02_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP01_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 140000
      distance empty: 55961.05 m
      sailing empty:  1.60 m/s
      duration:       9.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 139000
      by:             Transport barge 02 contains: 1000
      to:             KP02_levvel contains: 0
      distance empty: 57825.26 m
      sailing empty:  1.60 m/s
      duration:       10.04 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 125000
      by:             Transport barge 01 contains: 1000
      to:             KP04_clay contains: 4000
      distance full:  6394.29 m
      sailing full:   1.00 m/s
      duration:       1.78 hrs
    T=2253600.00 Condition: Site_KP05_clay.container.level<5000 and Site_KP04_clay.container.level==5000 is satisfied
    T=2253600.00 Condition: Site_KP05_clay.container.level<5000 and Site_KP04_clay.container.level==5000 is satisfied
    T=2253600.00 Condition: Site_KP04_sand.container.level<5000 and Site_KP03_sand.container.level==5000 and Site_KP04_clay.container.level==5000 is satisfied
    T=2253600.00 Clay placement to KP05_clay started
    T=2253600.00 Clay placement to KP05_clay started
    T=2253600.00 Sand placement to KP04_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 129000
      by:             Hopper contains: 1000
      to:             KP04_sand contains: 0
      distance full:  11355.64 m
      sailing full:   1.50 m/s
      duration:       2.10 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP04_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 129000
      distance empty: 11355.64 m
      sailing empty:  2.00 m/s
      duration:       1.58 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 128000
      by:             Hopper contains: 1000
      to:             KP04_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP04_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 125000
      distance full:  11355.64 m
      sailing full:   1.50 m/s
      duration:       2.10 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP04_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 128000
      distance empty: 6394.29 m
      sailing empty:  1.60 m/s
      duration:       1.11 hrs
      distance empty: 11355.64 m
      sailing empty:  2.00 m/s
      duration:       1.58 hrs
      distance full:  56990.66 m
      sailing full:   1.00 m/s
      duration:       15.83 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 127000
      by:             Hopper contains: 1000
      to:             KP04_sand contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 132000
      by:             Transport barge 01 contains: 1000
      to:             KP03_armour contains: 2000
      distance full:  11355.64 m
      sailing full:   1.50 m/s
      duration:       2.10 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP04_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 127000
      distance empty: 11355.64 m
      sailing empty:  2.00 m/s
      duration:       1.58 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 126000
      by:             Hopper contains: 1000
      to:             KP04_sand contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 139000
      distance full:  11355.64 m
      sailing full:   1.50 m/s
      duration:       2.10 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP04_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 126000
      distance empty: 11355.64 m
      sailing empty:  2.00 m/s
      duration:       1.58 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 125000
      by:             Hopper contains: 1000
      to:             KP04_sand contains: 4000
      distance full:  11355.64 m
      sailing full:   1.50 m/s
      duration:       2.10 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP04_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 125000
      distance empty: 11355.64 m
      sailing empty:  2.00 m/s
      duration:       1.58 hrs
      distance empty: 56990.66 m
      sailing empty:  1.60 m/s
      duration:       9.89 hrs
      distance full:  55961.05 m
      sailing full:   1.00 m/s
      duration:       15.54 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 131000
      by:             Transport barge 02 contains: 1000
      to:             KP03_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 131000
      distance empty: 55961.05 m
      sailing empty:  1.60 m/s
      duration:       9.72 hrs
      distance full:  55961.05 m
      sailing full:   1.00 m/s
      duration:       15.54 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 138000
      by:             Transport barge 01 contains: 1000
      to:             KP02_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 131000
      distance empty: 55961.05 m
      sailing empty:  1.60 m/s
      duration:       9.72 hrs
      distance full:  56990.66 m
      sailing full:   1.00 m/s
      duration:       15.83 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 124000
      by:             Transport barge 02 contains: 1000
      to:             KP05_clay contains: 0
      distance full:  7485.21 m
      sailing full:   1.00 m/s
      duration:       2.08 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 138000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 124000
      distance empty: 7485.21 m
      sailing empty:  1.60 m/s
      duration:       1.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 137000
      by:             Transport barge 02 contains: 1000
      to:             KP02_levvel contains: 2000
      distance empty: 56990.66 m
      sailing empty:  1.60 m/s
      duration:       9.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 123000
      by:             Transport barge 01 contains: 1000
      to:             KP05_clay contains: 1000
      distance full:  7485.21 m
      sailing full:   1.00 m/s
      duration:       2.08 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 123000
      distance empty: 7485.21 m
      sailing empty:  1.60 m/s
      duration:       1.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 130000
      by:             Transport barge 01 contains: 1000
      to:             KP03_armour contains: 4000
      distance full:  56990.66 m
      sailing full:   1.00 m/s
      duration:       15.83 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP02_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 137000
      distance full:  55961.05 m
      sailing full:   1.00 m/s
      duration:       15.54 hrs
    T=2631600.00 Condition: Site_KP04_armour.container.level<5000 and Site_KP03_armour.container.level==5000 and Site_KP04_sand.container.level==5000 is satisfied
    T=2631600.00 Condition: Site_KP04_armour.container.level<5000 and Site_KP03_armour.container.level==5000 and Site_KP04_sand.container.level==5000 is satisfied
    T=2631600.00 Armour placement to KP04_armour started
    T=2631600.00 Armour placement to KP04_armour started
      distance empty: 56990.66 m
      sailing empty:  1.60 m/s
      duration:       9.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 122000
      by:             Transport barge 02 contains: 1000
      to:             KP05_clay contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 130000
      distance full:  7485.21 m
      sailing full:   1.00 m/s
      duration:       2.08 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 122000
      distance empty: 7485.21 m
      sailing empty:  1.60 m/s
      duration:       1.30 hrs
      distance empty: 55961.05 m
      sailing empty:  1.60 m/s
      duration:       9.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 129000
      by:             Transport barge 02 contains: 1000
      to:             KP04_armour contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 136000
      by:             Transport barge 01 contains: 1000
      to:             KP02_levvel contains: 3000
      distance full:  55145.43 m
      sailing full:   1.00 m/s
      duration:       15.32 hrs
      distance full:  56990.66 m
      sailing full:   1.00 m/s
      duration:       15.83 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 129000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 136000
      distance empty: 55145.43 m
      sailing empty:  1.60 m/s
      duration:       9.57 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 135000
      by:             Transport barge 02 contains: 1000
      to:             KP02_levvel contains: 4000
      distance empty: 56990.66 m
      sailing empty:  1.60 m/s
      duration:       9.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 121000
      by:             Transport barge 01 contains: 1000
      to:             KP05_clay contains: 3000
      distance full:  7485.21 m
      sailing full:   1.00 m/s
      duration:       2.08 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 121000
      distance empty: 7485.21 m
      sailing empty:  1.60 m/s
      duration:       1.30 hrs
      distance full:  56990.66 m
      sailing full:   1.00 m/s
      duration:       15.83 hrs
    T=2862000.00 Condition: Site_KP03_levvel.container.level<5000 and Site_KP02_levvel.container.level==5000 and Site_KP03_armour.container.level==5000 is satisfied
    T=2862000.00 Condition: Site_KP03_levvel.container.level<5000 and Site_KP02_levvel.container.level==5000 and Site_KP03_armour.container.level==5000 is satisfied
    T=2862000.00 Block placement to KP03_levvel started
    T=2862000.00 Block placement to KP03_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 128000
      by:             Transport barge 01 contains: 1000
      to:             KP04_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP02_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 135000
      distance empty: 56990.66 m
      sailing empty:  1.60 m/s
      duration:       9.89 hrs
      distance full:  55145.43 m
      sailing full:   1.00 m/s
      duration:       15.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 120000
      by:             Transport barge 02 contains: 1000
      to:             KP05_clay contains: 4000
      distance full:  7485.21 m
      sailing full:   1.00 m/s
      duration:       2.08 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 128000
    T=2944800.00 Condition: Site_KP06_clay.container.level<5000 and Site_KP05_clay.container.level==5000 is satisfied
    T=2944800.00 Condition: Site_KP06_clay.container.level<5000 and Site_KP05_clay.container.level==5000 is satisfied
    T=2944800.00 Condition: Site_KP05_sand.container.level<5000 and Site_KP04_sand.container.level==5000 and Site_KP05_clay.container.level==5000 is satisfied
    T=2944800.00 Clay placement to KP06_clay started
    T=2944800.00 Clay placement to KP06_clay started
    T=2944800.00 Sand placement to KP05_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 124000
      by:             Hopper contains: 1000
      to:             KP05_sand contains: 0
      distance full:  10572.03 m
      sailing full:   1.50 m/s
      duration:       1.96 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP05_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 124000
      distance empty: 10572.03 m
      sailing empty:  2.00 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 123000
      by:             Hopper contains: 1000
      to:             KP05_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 120000
      distance full:  10572.03 m
      sailing full:   1.50 m/s
      duration:       1.96 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP05_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 123000
      distance empty: 7485.21 m
      sailing empty:  1.60 m/s
      duration:       1.30 hrs
      distance empty: 10572.03 m
      sailing empty:  2.00 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 122000
      by:             Hopper contains: 1000
      to:             KP05_sand contains: 2000
      distance empty: 55145.43 m
      sailing empty:  1.60 m/s
      duration:       9.57 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 127000
      by:             Transport barge 02 contains: 1000
      to:             KP04_armour contains: 2000
      distance full:  10572.03 m
      sailing full:   1.50 m/s
      duration:       1.96 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP05_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 122000
      distance empty: 10572.03 m
      sailing empty:  2.00 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 121000
      by:             Hopper contains: 1000
      to:             KP05_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 134000
      by:             Transport barge 01 contains: 1000
      to:             KP03_levvel contains: 0
      distance full:  10572.03 m
      sailing full:   1.50 m/s
      duration:       1.96 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP05_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 121000
      distance empty: 10572.03 m
      sailing empty:  2.00 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 120000
      by:             Hopper contains: 1000
      to:             KP05_sand contains: 4000
      distance full:  10572.03 m
      sailing full:   1.50 m/s
      duration:       1.96 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP05_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 120000
      distance empty: 10572.03 m
      sailing empty:  2.00 m/s
      duration:       1.47 hrs
      distance full:  55145.43 m
      sailing full:   1.00 m/s
      duration:       15.32 hrs
      distance full:  56166.60 m
      sailing full:   1.00 m/s
      duration:       15.60 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 127000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 134000
      distance empty: 55145.43 m
      sailing empty:  1.60 m/s
      duration:       9.57 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 133000
      by:             Transport barge 02 contains: 1000
      to:             KP03_levvel contains: 1000
      distance empty: 56166.60 m
      sailing empty:  1.60 m/s
      duration:       9.75 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 119000
      by:             Transport barge 01 contains: 1000
      to:             KP06_clay contains: 0
      distance full:  8585.26 m
      sailing full:   1.00 m/s
      duration:       2.38 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP06_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 119000
      distance empty: 8585.26 m
      sailing empty:  1.60 m/s
      duration:       1.49 hrs
      distance full:  56166.60 m
      sailing full:   1.00 m/s
      duration:       15.60 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 126000
      by:             Transport barge 01 contains: 1000
      to:             KP04_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 133000
      distance empty: 56166.60 m
      sailing empty:  1.60 m/s
      duration:       9.75 hrs
      distance full:  55145.43 m
      sailing full:   1.00 m/s
      duration:       15.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 118000
      by:             Transport barge 02 contains: 1000
      to:             KP06_clay contains: 1000
      distance full:  8585.26 m
      sailing full:   1.00 m/s
      duration:       2.38 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 126000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 118000
      distance empty: 8585.26 m
      sailing empty:  1.60 m/s
      duration:       1.49 hrs
      distance empty: 55145.43 m
      sailing empty:  1.60 m/s
      duration:       9.57 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 125000
      by:             Transport barge 02 contains: 1000
      to:             KP04_armour contains: 4000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 132000
      by:             Transport barge 01 contains: 1000
      to:             KP03_levvel contains: 2000
      distance full:  55145.43 m
      sailing full:   1.00 m/s
      duration:       15.32 hrs
    T=3330000.00 Condition: Site_KP05_armour.container.level<5000 and Site_KP04_armour.container.level==5000 and Site_KP05_sand.container.level==5000 is satisfied
    T=3330000.00 Condition: Site_KP05_armour.container.level<5000 and Site_KP04_armour.container.level==5000 and Site_KP05_sand.container.level==5000 is satisfied
    T=3330000.00 Armour placement to KP05_armour started
    T=3330000.00 Armour placement to KP05_armour started
      distance full:  56166.60 m
      sailing full:   1.00 m/s
      duration:       15.60 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 125000
      process:        5.56 hrs
    Unloaded:
      from:           KP03_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 132000
      distance empty: 55145.43 m
      sailing empty:  1.60 m/s
      duration:       9.57 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 131000
      by:             Transport barge 02 contains: 1000
      to:             KP03_levvel contains: 3000
      distance empty: 56166.60 m
      sailing empty:  1.60 m/s
      duration:       9.75 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 117000
      by:             Transport barge 01 contains: 1000
      to:             KP06_clay contains: 2000
      distance full:  8585.26 m
      sailing full:   1.00 m/s
      duration:       2.38 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP06_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 117000
      distance empty: 8585.26 m
      sailing empty:  1.60 m/s
      duration:       1.49 hrs
      distance full:  56166.60 m
      sailing full:   1.00 m/s
      duration:       15.60 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 124000
      by:             Transport barge 01 contains: 1000
      to:             KP05_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP03_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 131000
      distance empty: 56166.60 m
      sailing empty:  1.60 m/s
      duration:       9.75 hrs
      distance full:  54341.22 m
      sailing full:   1.00 m/s
      duration:       15.09 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 116000
      by:             Transport barge 02 contains: 1000
      to:             KP06_clay contains: 3000
      distance full:  8585.26 m
      sailing full:   1.00 m/s
      duration:       2.38 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 124000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 116000
      distance empty: 8585.26 m
      sailing empty:  1.60 m/s
      duration:       1.49 hrs
      distance empty: 54341.22 m
      sailing empty:  1.60 m/s
      duration:       9.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 123000
      by:             Transport barge 02 contains: 1000
      to:             KP05_armour contains: 1000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 130000
      by:             Transport barge 01 contains: 1000
      to:             KP03_levvel contains: 4000
      distance full:  54341.22 m
      sailing full:   1.00 m/s
      duration:       15.09 hrs
      distance full:  56166.60 m
      sailing full:   1.00 m/s
      duration:       15.60 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 123000
    T=3643200.00 Condition: Site_KP04_levvel.container.level<5000 and Site_KP03_levvel.container.level==5000 and Site_KP04_armour.container.level==5000 is satisfied
    T=3643200.00 Condition: Site_KP04_levvel.container.level<5000 and Site_KP03_levvel.container.level==5000 and Site_KP04_armour.container.level==5000 is satisfied
    T=3643200.00 Block placement to KP04_levvel started
    T=3643200.00 Block placement to KP04_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP03_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 130000
      distance empty: 54341.22 m
      sailing empty:  1.60 m/s
      duration:       9.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 129000
      by:             Transport barge 02 contains: 1000
      to:             KP04_levvel contains: 0
      distance empty: 56166.60 m
      sailing empty:  1.60 m/s
      duration:       9.75 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 115000
      by:             Transport barge 01 contains: 1000
      to:             KP06_clay contains: 4000
      distance full:  8585.26 m
      sailing full:   1.00 m/s
      duration:       2.38 hrs
    T=3715200.00 Condition: Site_KP07_clay.container.level<5000 and Site_KP06_clay.container.level==5000 is satisfied
    T=3715200.00 Condition: Site_KP07_clay.container.level<5000 and Site_KP06_clay.container.level==5000 is satisfied
    T=3715200.00 Condition: Site_KP06_sand.container.level<5000 and Site_KP05_sand.container.level==5000 and Site_KP06_clay.container.level==5000 is satisfied
    T=3715200.00 Clay placement to KP07_clay started
    T=3715200.00 Clay placement to KP07_clay started
    T=3715200.00 Sand placement to KP06_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 119000
      by:             Hopper contains: 1000
      to:             KP06_sand contains: 0
      distance full:  9855.66 m
      sailing full:   1.50 m/s
      duration:       1.83 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP06_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 119000
      distance empty: 9855.66 m
      sailing empty:  2.00 m/s
      duration:       1.37 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 118000
      by:             Hopper contains: 1000
      to:             KP06_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 115000
      distance full:  9855.66 m
      sailing full:   1.50 m/s
      duration:       1.83 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP06_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 118000
      distance empty: 8585.26 m
      sailing empty:  1.60 m/s
      duration:       1.49 hrs
      distance full:  55353.56 m
      sailing full:   1.00 m/s
      duration:       15.38 hrs
      distance empty: 9855.66 m
      sailing empty:  2.00 m/s
      duration:       1.37 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 117000
      by:             Hopper contains: 1000
      to:             KP06_sand contains: 2000
      distance full:  9855.66 m
      sailing full:   1.50 m/s
      duration:       1.83 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP06_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 117000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 122000
      by:             Transport barge 01 contains: 1000
      to:             KP05_armour contains: 2000
      distance empty: 9855.66 m
      sailing empty:  2.00 m/s
      duration:       1.37 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 116000
      by:             Hopper contains: 1000
      to:             KP06_sand contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP04_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 129000
      distance full:  9855.66 m
      sailing full:   1.50 m/s
      duration:       1.83 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP06_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 116000
      distance empty: 9855.66 m
      sailing empty:  2.00 m/s
      duration:       1.37 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 115000
      by:             Hopper contains: 1000
      to:             KP06_sand contains: 4000
      distance full:  9855.66 m
      sailing full:   1.50 m/s
      duration:       1.83 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP06_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 115000
      distance empty: 9855.66 m
      sailing empty:  2.00 m/s
      duration:       1.37 hrs
      distance empty: 55353.56 m
      sailing empty:  1.60 m/s
      duration:       9.61 hrs
      distance full:  54341.22 m
      sailing full:   1.00 m/s
      duration:       15.09 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 121000
      by:             Transport barge 02 contains: 1000
      to:             KP05_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 121000
      distance empty: 54341.22 m
      sailing empty:  1.60 m/s
      duration:       9.43 hrs
      distance full:  54341.22 m
      sailing full:   1.00 m/s
      duration:       15.09 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 128000
      by:             Transport barge 01 contains: 1000
      to:             KP04_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 121000
      distance empty: 54341.22 m
      sailing empty:  1.60 m/s
      duration:       9.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 114000
      by:             Transport barge 02 contains: 1000
      to:             KP07_clay contains: 0
      distance full:  55353.56 m
      sailing full:   1.00 m/s
      duration:       15.38 hrs
      distance full:  9691.31 m
      sailing full:   1.00 m/s
      duration:       2.69 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 128000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 114000
      distance empty: 9691.31 m
      sailing empty:  1.60 m/s
      duration:       1.68 hrs
      distance empty: 55353.56 m
      sailing empty:  1.60 m/s
      duration:       9.61 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 127000
      by:             Transport barge 02 contains: 1000
      to:             KP04_levvel contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 113000
      by:             Transport barge 01 contains: 1000
      to:             KP07_clay contains: 1000
      distance full:  9691.31 m
      sailing full:   1.00 m/s
      duration:       2.69 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP07_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 113000
      distance empty: 9691.31 m
      sailing empty:  1.60 m/s
      duration:       1.68 hrs
      distance full:  55353.56 m
      sailing full:   1.00 m/s
      duration:       15.38 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 120000
      by:             Transport barge 01 contains: 1000
      to:             KP05_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP04_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 127000
      distance empty: 55353.56 m
      sailing empty:  1.60 m/s
      duration:       9.61 hrs
      distance full:  54341.22 m
      sailing full:   1.00 m/s
      duration:       15.09 hrs
    T=4089600.00 Condition: Site_KP06_armour.container.level<5000 and Site_KP05_armour.container.level==5000 and Site_KP06_sand.container.level==5000 is satisfied
    T=4089600.00 Condition: Site_KP06_armour.container.level<5000 and Site_KP05_armour.container.level==5000 and Site_KP06_sand.container.level==5000 is satisfied
    T=4089600.00 Armour placement to KP06_armour started
    T=4089600.00 Armour placement to KP06_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 112000
      by:             Transport barge 02 contains: 1000
      to:             KP07_clay contains: 2000
      distance full:  9691.31 m
      sailing full:   1.00 m/s
      duration:       2.69 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 120000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 112000
      distance empty: 9691.31 m
      sailing empty:  1.60 m/s
      duration:       1.68 hrs
      distance empty: 54341.22 m
      sailing empty:  1.60 m/s
      duration:       9.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 126000
      by:             Transport barge 02 contains: 1000
      to:             KP04_levvel contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 125000
      by:             Transport barge 01 contains: 1000
      to:             KP04_levvel contains: 3000
      distance full:  55353.56 m
      sailing full:   1.00 m/s
      duration:       15.38 hrs
      distance full:  55353.56 m
      sailing full:   1.00 m/s
      duration:       15.38 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP04_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 125000
    T=4222800.00 Condition: Site_KP05_levvel.container.level<5000 and Site_KP04_levvel.container.level==5000 and Site_KP05_armour.container.level==5000 is satisfied
    T=4222800.00 Condition: Site_KP05_levvel.container.level<5000 and Site_KP04_levvel.container.level==5000 and Site_KP05_armour.container.level==5000 is satisfied
    T=4222800.00 Block placement to KP05_levvel started
    T=4222800.00 Block placement to KP05_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP04_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 125000
      distance empty: 55353.56 m
      sailing empty:  1.60 m/s
      duration:       9.61 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 119000
      by:             Transport barge 02 contains: 1000
      to:             KP06_armour contains: 0
      distance empty: 55353.56 m
      sailing empty:  1.60 m/s
      duration:       9.61 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 111000
      by:             Transport barge 01 contains: 1000
      to:             KP07_clay contains: 3000
      distance full:  9691.31 m
      sailing full:   1.00 m/s
      duration:       2.69 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP07_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 111000
      distance full:  53548.93 m
      sailing full:   1.00 m/s
      duration:       14.87 hrs
      distance empty: 9691.31 m
      sailing empty:  1.60 m/s
      duration:       1.68 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 118000
      by:             Transport barge 01 contains: 1000
      to:             KP06_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 118000
      distance empty: 53548.93 m
      sailing empty:  1.60 m/s
      duration:       9.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 110000
      by:             Transport barge 02 contains: 1000
      to:             KP07_clay contains: 4000
      distance full:  53548.93 m
      sailing full:   1.00 m/s
      duration:       14.87 hrs
      distance full:  9691.31 m
      sailing full:   1.00 m/s
      duration:       2.69 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP06_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 118000
    T=4406400.00 Condition: Site_KP08_clay.container.level<5000 and Site_KP07_clay.container.level==5000 is satisfied
    T=4406400.00 Condition: Site_KP08_clay.container.level<5000 and Site_KP07_clay.container.level==5000 is satisfied
    T=4406400.00 Condition: Site_KP07_sand.container.level<5000 and Site_KP06_sand.container.level==5000 and Site_KP07_clay.container.level==5000 is satisfied
    T=4406400.00 Clay placement to KP08_clay started
    T=4406400.00 Clay placement to KP08_clay started
    T=4406400.00 Sand placement to KP07_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 114000
      by:             Hopper contains: 1000
      to:             KP07_sand contains: 0
      distance full:  9222.16 m
      sailing full:   1.50 m/s
      duration:       1.71 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP07_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 114000
      distance empty: 9222.16 m
      sailing empty:  2.00 m/s
      duration:       1.28 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 113000
      by:             Hopper contains: 1000
      to:             KP07_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 110000
      distance full:  9222.16 m
      sailing full:   1.50 m/s
      duration:       1.71 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP07_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 113000
      distance empty: 9222.16 m
      sailing empty:  2.00 m/s
      duration:       1.28 hrs
      distance empty: 9691.31 m
      sailing empty:  1.60 m/s
      duration:       1.68 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 112000
      by:             Hopper contains: 1000
      to:             KP07_sand contains: 2000
      distance full:  9222.16 m
      sailing full:   1.50 m/s
      duration:       1.71 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP07_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 112000
      distance empty: 53548.93 m
      sailing empty:  1.60 m/s
      duration:       9.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 124000
      by:             Transport barge 02 contains: 1000
      to:             KP05_levvel contains: 0
      distance empty: 9222.16 m
      sailing empty:  2.00 m/s
      duration:       1.28 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 111000
      by:             Hopper contains: 1000
      to:             KP07_sand contains: 3000
      distance full:  9222.16 m
      sailing full:   1.50 m/s
      duration:       1.71 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP07_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 111000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 123000
      by:             Transport barge 01 contains: 1000
      to:             KP05_levvel contains: 0
      distance empty: 9222.16 m
      sailing empty:  2.00 m/s
      duration:       1.28 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 110000
      by:             Hopper contains: 1000
      to:             KP07_sand contains: 4000
      distance full:  9222.16 m
      sailing full:   1.50 m/s
      duration:       1.71 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP07_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 110000
      distance empty: 9222.16 m
      sailing empty:  2.00 m/s
      duration:       1.28 hrs
      distance full:  54552.02 m
      sailing full:   1.00 m/s
      duration:       15.15 hrs
      distance full:  54552.02 m
      sailing full:   1.00 m/s
      duration:       15.15 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 123000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 123000
      distance empty: 54552.02 m
      sailing empty:  1.60 m/s
      duration:       9.47 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 117000
      by:             Transport barge 02 contains: 1000
      to:             KP06_armour contains: 2000
      distance empty: 54552.02 m
      sailing empty:  1.60 m/s
      duration:       9.47 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 109000
      by:             Transport barge 01 contains: 1000
      to:             KP08_clay contains: 0
      distance full:  10801.49 m
      sailing full:   1.00 m/s
      duration:       3.00 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 109000
      distance full:  53548.93 m
      sailing full:   1.00 m/s
      duration:       14.87 hrs
      distance empty: 10801.49 m
      sailing empty:  1.60 m/s
      duration:       1.88 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 116000
      by:             Transport barge 01 contains: 1000
      to:             KP06_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 116000
      distance empty: 53548.93 m
      sailing empty:  1.60 m/s
      duration:       9.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 108000
      by:             Transport barge 02 contains: 1000
      to:             KP08_clay contains: 1000
      distance full:  53548.93 m
      sailing full:   1.00 m/s
      duration:       14.87 hrs
      distance full:  10801.49 m
      sailing full:   1.00 m/s
      duration:       3.00 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP06_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 116000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 108000
      distance empty: 10801.49 m
      sailing empty:  1.60 m/s
      duration:       1.88 hrs
      distance empty: 53548.93 m
      sailing empty:  1.60 m/s
      duration:       9.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 122000
      by:             Transport barge 02 contains: 1000
      to:             KP05_levvel contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 121000
      by:             Transport barge 01 contains: 1000
      to:             KP05_levvel contains: 2000
      distance full:  54552.02 m
      sailing full:   1.00 m/s
      duration:       15.15 hrs
      distance full:  54552.02 m
      sailing full:   1.00 m/s
      duration:       15.15 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP05_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 121000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 121000
      distance empty: 54552.02 m
      sailing empty:  1.60 m/s
      duration:       9.47 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 115000
      by:             Transport barge 02 contains: 1000
      to:             KP06_armour contains: 4000
      distance empty: 54552.02 m
      sailing empty:  1.60 m/s
      duration:       9.47 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 107000
      by:             Transport barge 01 contains: 1000
      to:             KP08_clay contains: 2000
      distance full:  10801.49 m
      sailing full:   1.00 m/s
      duration:       3.00 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 107000
      distance full:  53548.93 m
      sailing full:   1.00 m/s
      duration:       14.87 hrs
    T=4910400.00 Condition: Site_KP07_armour.container.level<5000 and Site_KP06_armour.container.level==5000 and Site_KP07_sand.container.level==5000 is satisfied
    T=4910400.00 Condition: Site_KP07_armour.container.level<5000 and Site_KP06_armour.container.level==5000 and Site_KP07_sand.container.level==5000 is satisfied
    T=4910400.00 Armour placement to KP07_armour started
    T=4910400.00 Armour placement to KP07_armour started
      distance empty: 10801.49 m
      sailing empty:  1.60 m/s
      duration:       1.88 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 114000
      by:             Transport barge 01 contains: 1000
      to:             KP07_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP06_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 114000
      distance empty: 53548.93 m
      sailing empty:  1.60 m/s
      duration:       9.30 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 106000
      by:             Transport barge 02 contains: 1000
      to:             KP08_clay contains: 3000
      distance full:  52769.10 m
      sailing full:   1.00 m/s
      duration:       14.66 hrs
      distance full:  10801.49 m
      sailing full:   1.00 m/s
      duration:       3.00 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP07_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 114000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 106000
      distance empty: 10801.49 m
      sailing empty:  1.60 m/s
      duration:       1.88 hrs
      distance empty: 52769.10 m
      sailing empty:  1.60 m/s
      duration:       9.16 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 120000
      by:             Transport barge 02 contains: 1000
      to:             KP05_levvel contains: 4000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 105000
      by:             Transport barge 01 contains: 1000
      to:             KP08_clay contains: 4000
      distance full:  10801.49 m
      sailing full:   1.00 m/s
      duration:       3.00 hrs
    T=5054400.00 Condition: Site_KP09_clay.container.level<5000 and Site_KP08_clay.container.level==5000 is satisfied
    T=5054400.00 Condition: Site_KP09_clay.container.level<5000 and Site_KP08_clay.container.level==5000 is satisfied
    T=5054400.00 Condition: Site_KP08_sand.container.level<5000 and Site_KP07_sand.container.level==5000 and Site_KP08_clay.container.level==5000 is satisfied
    T=5054400.00 Clay placement to KP09_clay started
    T=5054400.00 Clay placement to KP09_clay started
    T=5054400.00 Sand placement to KP08_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 109000
      by:             Hopper contains: 1000
      to:             KP08_sand contains: 0
      distance full:  8689.66 m
      sailing full:   1.50 m/s
      duration:       1.61 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP08_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 109000
      distance empty: 8689.66 m
      sailing empty:  2.00 m/s
      duration:       1.21 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 108000
      by:             Hopper contains: 1000
      to:             KP08_sand contains: 1000
      distance full:  8689.66 m
      sailing full:   1.50 m/s
      duration:       1.61 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP08_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 108000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 105000
      distance empty: 8689.66 m
      sailing empty:  2.00 m/s
      duration:       1.21 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 107000
      by:             Hopper contains: 1000
      to:             KP08_sand contains: 2000
      distance empty: 10801.49 m
      sailing empty:  1.60 m/s
      duration:       1.88 hrs
      distance full:  8689.66 m
      sailing full:   1.50 m/s
      duration:       1.61 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP08_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 107000
      distance full:  54552.02 m
      sailing full:   1.00 m/s
      duration:       15.15 hrs
    T=5086800.00 Condition: Site_KP06_levvel.container.level<5000 and Site_KP05_levvel.container.level==5000 and Site_KP06_armour.container.level==5000 is satisfied
    T=5086800.00 Condition: Site_KP06_levvel.container.level<5000 and Site_KP05_levvel.container.level==5000 and Site_KP06_armour.container.level==5000 is satisfied
    T=5086800.00 Block placement to KP06_levvel started
    T=5086800.00 Block placement to KP06_levvel started
      distance empty: 8689.66 m
      sailing empty:  2.00 m/s
      duration:       1.21 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 106000
      by:             Hopper contains: 1000
      to:             KP08_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 113000
      by:             Transport barge 01 contains: 1000
      to:             KP07_armour contains: 1000
      distance full:  8689.66 m
      sailing full:   1.50 m/s
      duration:       1.61 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP08_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 106000
      distance empty: 8689.66 m
      sailing empty:  2.00 m/s
      duration:       1.21 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 105000
      by:             Hopper contains: 1000
      to:             KP08_sand contains: 4000
      distance full:  8689.66 m
      sailing full:   1.50 m/s
      duration:       1.61 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP08_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 105000
      process:        5.56 hrs
    Unloaded:
      from:           KP05_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 120000
      distance empty: 8689.66 m
      sailing empty:  2.00 m/s
      duration:       1.21 hrs
      distance empty: 54552.02 m
      sailing empty:  1.60 m/s
      duration:       9.47 hrs
      distance full:  52769.10 m
      sailing full:   1.00 m/s
      duration:       14.66 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 112000
      by:             Transport barge 02 contains: 1000
      to:             KP07_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 112000
      distance empty: 52769.10 m
      sailing empty:  1.60 m/s
      duration:       9.16 hrs
      distance full:  52769.10 m
      sailing full:   1.00 m/s
      duration:       14.66 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 104000
      by:             Transport barge 01 contains: 1000
      to:             KP09_clay contains: 0
      distance full:  11914.60 m
      sailing full:   1.00 m/s
      duration:       3.31 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP07_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 112000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 104000
      distance empty: 11914.60 m
      sailing empty:  1.60 m/s
      duration:       2.07 hrs
      distance empty: 52769.10 m
      sailing empty:  1.60 m/s
      duration:       9.16 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 119000
      by:             Transport barge 01 contains: 1000
      to:             KP06_levvel contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 103000
      by:             Transport barge 02 contains: 1000
      to:             KP09_clay contains: 1000
      distance full:  11914.60 m
      sailing full:   1.00 m/s
      duration:       3.31 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 103000
      distance empty: 11914.60 m
      sailing empty:  1.60 m/s
      duration:       2.07 hrs
      distance full:  53762.49 m
      sailing full:   1.00 m/s
      duration:       14.93 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 118000
      by:             Transport barge 02 contains: 1000
      to:             KP06_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 118000
      distance empty: 53762.49 m
      sailing empty:  1.60 m/s
      duration:       9.33 hrs
      distance full:  53762.49 m
      sailing full:   1.00 m/s
      duration:       14.93 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 111000
      by:             Transport barge 01 contains: 1000
      to:             KP07_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 118000
      distance empty: 53762.49 m
      sailing empty:  1.60 m/s
      duration:       9.33 hrs
      distance full:  52769.10 m
      sailing full:   1.00 m/s
      duration:       14.66 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 110000
      by:             Transport barge 02 contains: 1000
      to:             KP07_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 110000
      distance empty: 52769.10 m
      sailing empty:  1.60 m/s
      duration:       9.16 hrs
      distance full:  52769.10 m
      sailing full:   1.00 m/s
      duration:       14.66 hrs
    T=5493600.00 Condition: Site_KP08_armour.container.level<5000 and Site_KP07_armour.container.level==5000 and Site_KP08_sand.container.level==5000 is satisfied
    T=5493600.00 Condition: Site_KP08_armour.container.level<5000 and Site_KP07_armour.container.level==5000 and Site_KP08_sand.container.level==5000 is satisfied
    T=5493600.00 Armour placement to KP08_armour started
    T=5493600.00 Armour placement to KP08_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 102000
      by:             Transport barge 01 contains: 1000
      to:             KP09_clay contains: 2000
      distance full:  11914.60 m
      sailing full:   1.00 m/s
      duration:       3.31 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP07_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 110000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 102000
      distance empty: 11914.60 m
      sailing empty:  1.60 m/s
      duration:       2.07 hrs
      distance empty: 52769.10 m
      sailing empty:  1.60 m/s
      duration:       9.16 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 117000
      by:             Transport barge 01 contains: 1000
      to:             KP06_levvel contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 101000
      by:             Transport barge 02 contains: 1000
      to:             KP09_clay contains: 3000
      distance full:  11914.60 m
      sailing full:   1.00 m/s
      duration:       3.31 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 101000
      distance empty: 11914.60 m
      sailing empty:  1.60 m/s
      duration:       2.07 hrs
      distance full:  53762.49 m
      sailing full:   1.00 m/s
      duration:       14.93 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 116000
      by:             Transport barge 02 contains: 1000
      to:             KP06_levvel contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 116000
      distance empty: 53762.49 m
      sailing empty:  1.60 m/s
      duration:       9.33 hrs
      distance full:  53762.49 m
      sailing full:   1.00 m/s
      duration:       14.93 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 109000
      by:             Transport barge 01 contains: 1000
      to:             KP08_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP06_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 116000
      distance empty: 53762.49 m
      sailing empty:  1.60 m/s
      duration:       9.33 hrs
      distance full:  52002.27 m
      sailing full:   1.00 m/s
      duration:       14.45 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 108000
      by:             Transport barge 02 contains: 1000
      to:             KP08_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 108000
      distance empty: 52002.27 m
      sailing empty:  1.60 m/s
      duration:       9.03 hrs
      distance full:  52002.27 m
      sailing full:   1.00 m/s
      duration:       14.45 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 100000
      by:             Transport barge 01 contains: 1000
      to:             KP09_clay contains: 4000
      distance full:  11914.60 m
      sailing full:   1.00 m/s
      duration:       3.31 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 108000
    T=5799600.00 Condition: Site_KP10_clay.container.level<5000 and Site_KP09_clay.container.level==5000 is satisfied
    T=5799600.00 Condition: Site_KP10_clay.container.level<5000 and Site_KP09_clay.container.level==5000 is satisfied
    T=5799600.00 Condition: Site_KP09_sand.container.level<5000 and Site_KP08_sand.container.level==5000 and Site_KP09_clay.container.level==5000 is satisfied
    T=5799600.00 Clay placement to KP10_clay started
    T=5799600.00 Clay placement to KP10_clay started
    T=5799600.00 Sand placement to KP09_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 104000
      by:             Hopper contains: 1000
      to:             KP09_sand contains: 0
      distance full:  8277.61 m
      sailing full:   1.50 m/s
      duration:       1.53 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP09_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 104000
      distance empty: 8277.61 m
      sailing empty:  2.00 m/s
      duration:       1.15 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 103000
      by:             Hopper contains: 1000
      to:             KP09_sand contains: 1000
      distance full:  8277.61 m
      sailing full:   1.50 m/s
      duration:       1.53 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 100000
      process:        0.14 hrs
    Unloaded:
      from:           KP09_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 103000
      distance empty: 8277.61 m
      sailing empty:  2.00 m/s
      duration:       1.15 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 102000
      by:             Hopper contains: 1000
      to:             KP09_sand contains: 2000
      distance empty: 11914.60 m
      sailing empty:  1.60 m/s
      duration:       2.07 hrs
      distance full:  8277.61 m
      sailing full:   1.50 m/s
      duration:       1.53 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP09_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 102000
      distance empty: 52002.27 m
      sailing empty:  1.60 m/s
      duration:       9.03 hrs
      distance empty: 8277.61 m
      sailing empty:  2.00 m/s
      duration:       1.15 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 101000
      by:             Hopper contains: 1000
      to:             KP09_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 115000
      by:             Transport barge 01 contains: 1000
      to:             KP06_levvel contains: 4000
      distance full:  8277.61 m
      sailing full:   1.50 m/s
      duration:       1.53 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP09_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 101000
      distance empty: 8277.61 m
      sailing empty:  2.00 m/s
      duration:       1.15 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 100000
      by:             Hopper contains: 1000
      to:             KP09_sand contains: 4000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 99000
      by:             Transport barge 02 contains: 1000
      to:             KP10_clay contains: 0
      distance full:  8277.61 m
      sailing full:   1.50 m/s
      duration:       1.53 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP09_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 100000
      distance empty: 8277.61 m
      sailing empty:  2.00 m/s
      duration:       1.15 hrs
      distance full:  13029.88 m
      sailing full:   1.00 m/s
      duration:       3.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 99000
      distance empty: 13029.88 m
      sailing empty:  1.60 m/s
      duration:       2.26 hrs
      distance full:  53762.49 m
      sailing full:   1.00 m/s
      duration:       14.93 hrs
    T=5889600.00 Condition: Site_KP07_levvel.container.level<5000 and Site_KP06_levvel.container.level==5000 and Site_KP07_armour.container.level==5000 is satisfied
    T=5889600.00 Condition: Site_KP07_levvel.container.level<5000 and Site_KP06_levvel.container.level==5000 and Site_KP07_armour.container.level==5000 is satisfied
    T=5889600.00 Block placement to KP07_levvel started
    T=5889600.00 Block placement to KP07_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 107000
      by:             Transport barge 02 contains: 1000
      to:             KP08_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP06_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 115000
      distance empty: 53762.49 m
      sailing empty:  1.60 m/s
      duration:       9.33 hrs
      distance full:  52002.27 m
      sailing full:   1.00 m/s
      duration:       14.45 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 106000
      by:             Transport barge 01 contains: 1000
      to:             KP08_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 106000
      distance empty: 52002.27 m
      sailing empty:  1.60 m/s
      duration:       9.03 hrs
      distance full:  52002.27 m
      sailing full:   1.00 m/s
      duration:       14.45 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 98000
      by:             Transport barge 02 contains: 1000
      to:             KP10_clay contains: 1000
      distance full:  13029.88 m
      sailing full:   1.00 m/s
      duration:       3.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 106000
      process:        5.56 hrs
    Unloaded:
      from:           KP10_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 98000
      distance empty: 13029.88 m
      sailing empty:  1.60 m/s
      duration:       2.26 hrs
      distance empty: 52002.27 m
      sailing empty:  1.60 m/s
      duration:       9.03 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 114000
      by:             Transport barge 02 contains: 1000
      to:             KP07_levvel contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 97000
      by:             Transport barge 01 contains: 1000
      to:             KP10_clay contains: 2000
      distance full:  13029.88 m
      sailing full:   1.00 m/s
      duration:       3.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 97000
      distance empty: 13029.88 m
      sailing empty:  1.60 m/s
      duration:       2.26 hrs
      distance full:  52985.50 m
      sailing full:   1.00 m/s
      duration:       14.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 113000
      by:             Transport barge 01 contains: 1000
      to:             KP07_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 113000
      distance empty: 52985.50 m
      sailing empty:  1.60 m/s
      duration:       9.20 hrs
      distance full:  52985.50 m
      sailing full:   1.00 m/s
      duration:       14.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 105000
      by:             Transport barge 02 contains: 1000
      to:             KP08_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 113000
      distance empty: 52985.50 m
      sailing empty:  1.60 m/s
      duration:       9.20 hrs
      distance full:  52002.27 m
      sailing full:   1.00 m/s
      duration:       14.45 hrs
    T=6231600.00 Condition: Site_KP09_armour.container.level<5000 and Site_KP08_armour.container.level==5000 and Site_KP09_sand.container.level==5000 is satisfied
    T=6231600.00 Condition: Site_KP09_armour.container.level<5000 and Site_KP08_armour.container.level==5000 and Site_KP09_sand.container.level==5000 is satisfied
    T=6231600.00 Armour placement to KP09_armour started
    T=6231600.00 Armour placement to KP09_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 96000
      by:             Transport barge 01 contains: 1000
      to:             KP10_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 105000
      distance full:  13029.88 m
      sailing full:   1.00 m/s
      duration:       3.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 96000
      distance empty: 13029.88 m
      sailing empty:  1.60 m/s
      duration:       2.26 hrs
      distance empty: 52002.27 m
      sailing empty:  1.60 m/s
      duration:       9.03 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 112000
      by:             Transport barge 01 contains: 1000
      to:             KP07_levvel contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 95000
      by:             Transport barge 02 contains: 1000
      to:             KP10_clay contains: 4000
      distance full:  13029.88 m
      sailing full:   1.00 m/s
      duration:       3.62 hrs
    T=6314400.00 Condition: Site_KP11_clay.container.level<5000 and Site_KP10_clay.container.level==5000 is satisfied
    T=6314400.00 Condition: Site_KP11_clay.container.level<5000 and Site_KP10_clay.container.level==5000 is satisfied
    T=6314400.00 Condition: Site_KP10_sand.container.level<5000 and Site_KP09_sand.container.level==5000 and Site_KP10_clay.container.level==5000 is satisfied
    T=6314400.00 Clay placement to KP11_clay started
    T=6314400.00 Clay placement to KP11_clay started
    T=6314400.00 Sand placement to KP10_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 99000
      by:             Hopper contains: 1000
      to:             KP10_sand contains: 0
      distance full:  8004.61 m
      sailing full:   1.50 m/s
      duration:       1.48 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP10_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 99000
      distance empty: 8004.61 m
      sailing empty:  2.00 m/s
      duration:       1.11 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 98000
      by:             Hopper contains: 1000
      to:             KP10_sand contains: 1000
      distance full:  8004.61 m
      sailing full:   1.50 m/s
      duration:       1.48 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP10_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 98000
      process:        5.56 hrs
    Unloaded:
      from:           KP10_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 95000
      distance empty: 8004.61 m
      sailing empty:  2.00 m/s
      duration:       1.11 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 97000
      by:             Hopper contains: 1000
      to:             KP10_sand contains: 2000
      distance full:  8004.61 m
      sailing full:   1.50 m/s
      duration:       1.48 hrs
      distance empty: 13029.88 m
      sailing empty:  1.60 m/s
      duration:       2.26 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP10_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 97000
      distance full:  52985.50 m
      sailing full:   1.00 m/s
      duration:       14.72 hrs
      distance empty: 8004.61 m
      sailing empty:  2.00 m/s
      duration:       1.11 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 96000
      by:             Hopper contains: 1000
      to:             KP10_sand contains: 3000
      distance full:  8004.61 m
      sailing full:   1.50 m/s
      duration:       1.48 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 111000
      by:             Transport barge 02 contains: 1000
      to:             KP07_levvel contains: 3000
      process:        0.14 hrs
    Unloaded:
      from:           KP10_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 96000
      distance empty: 8004.61 m
      sailing empty:  2.00 m/s
      duration:       1.11 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 95000
      by:             Hopper contains: 1000
      to:             KP10_sand contains: 4000
      distance full:  8004.61 m
      sailing full:   1.50 m/s
      duration:       1.48 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP10_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 95000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 111000
      distance empty: 8004.61 m
      sailing empty:  2.00 m/s
      duration:       1.11 hrs
      distance empty: 52985.50 m
      sailing empty:  1.60 m/s
      duration:       9.20 hrs
      distance full:  52985.50 m
      sailing full:   1.00 m/s
      duration:       14.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 104000
      by:             Transport barge 01 contains: 1000
      to:             KP09_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP07_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 111000
      distance empty: 52985.50 m
      sailing empty:  1.60 m/s
      duration:       9.20 hrs
      distance full:  51249.04 m
      sailing full:   1.00 m/s
      duration:       14.24 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 103000
      by:             Transport barge 02 contains: 1000
      to:             KP09_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 103000
      distance empty: 51249.04 m
      sailing empty:  1.60 m/s
      duration:       8.90 hrs
      distance full:  51249.04 m
      sailing full:   1.00 m/s
      duration:       14.24 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 94000
      by:             Transport barge 01 contains: 1000
      to:             KP11_clay contains: 0
      distance full:  14146.78 m
      sailing full:   1.00 m/s
      duration:       3.93 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 103000
      process:        5.56 hrs
    Unloaded:
      from:           KP11_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 94000
      distance empty: 14146.78 m
      sailing empty:  1.60 m/s
      duration:       2.46 hrs
      distance empty: 51249.04 m
      sailing empty:  1.60 m/s
      duration:       8.90 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 110000
      by:             Transport barge 01 contains: 1000
      to:             KP07_levvel contains: 4000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 93000
      by:             Transport barge 02 contains: 1000
      to:             KP11_clay contains: 1000
      distance full:  14146.78 m
      sailing full:   1.00 m/s
      duration:       3.93 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 93000
      distance full:  52985.50 m
      sailing full:   1.00 m/s
      duration:       14.72 hrs
      distance empty: 14146.78 m
      sailing empty:  1.60 m/s
      duration:       2.46 hrs
    T=6631200.00 Condition: Site_KP08_levvel.container.level<5000 and Site_KP07_levvel.container.level==5000 and Site_KP08_armour.container.level==5000 is satisfied
    T=6631200.00 Condition: Site_KP08_levvel.container.level<5000 and Site_KP07_levvel.container.level==5000 and Site_KP08_armour.container.level==5000 is satisfied
    T=6631200.00 Block placement to KP08_levvel started
    T=6631200.00 Block placement to KP08_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 102000
      by:             Transport barge 02 contains: 1000
      to:             KP09_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP07_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 110000
      distance empty: 52985.50 m
      sailing empty:  1.60 m/s
      duration:       9.20 hrs
      distance full:  51249.04 m
      sailing full:   1.00 m/s
      duration:       14.24 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 101000
      by:             Transport barge 01 contains: 1000
      to:             KP09_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 101000
      distance empty: 51249.04 m
      sailing empty:  1.60 m/s
      duration:       8.90 hrs
      distance full:  51249.04 m
      sailing full:   1.00 m/s
      duration:       14.24 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 92000
      by:             Transport barge 02 contains: 1000
      to:             KP11_clay contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 101000
      distance full:  14146.78 m
      sailing full:   1.00 m/s
      duration:       3.93 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 92000
      distance empty: 14146.78 m
      sailing empty:  1.60 m/s
      duration:       2.46 hrs
      distance empty: 51249.04 m
      sailing empty:  1.60 m/s
      duration:       8.90 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 109000
      by:             Transport barge 02 contains: 1000
      to:             KP08_levvel contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 91000
      by:             Transport barge 01 contains: 1000
      to:             KP11_clay contains: 3000
      distance full:  14146.78 m
      sailing full:   1.00 m/s
      duration:       3.93 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 91000
      distance full:  52221.59 m
      sailing full:   1.00 m/s
      duration:       14.51 hrs
      distance empty: 14146.78 m
      sailing empty:  1.60 m/s
      duration:       2.46 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 108000
      by:             Transport barge 01 contains: 1000
      to:             KP08_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 108000
      distance empty: 52221.59 m
      sailing empty:  1.60 m/s
      duration:       9.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 100000
      by:             Transport barge 02 contains: 1000
      to:             KP09_armour contains: 4000
      distance full:  52221.59 m
      sailing full:   1.00 m/s
      duration:       14.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 108000
      distance full:  51249.04 m
      sailing full:   1.00 m/s
      duration:       14.24 hrs
    T=6973200.00 Condition: Site_KP10_armour.container.level<5000 and Site_KP09_armour.container.level==5000 and Site_KP10_sand.container.level==5000 is satisfied
    T=6973200.00 Condition: Site_KP10_armour.container.level<5000 and Site_KP09_armour.container.level==5000 and Site_KP10_sand.container.level==5000 is satisfied
    T=6973200.00 Armour placement to KP10_armour started
    T=6973200.00 Armour placement to KP10_armour started
      distance empty: 52221.59 m
      sailing empty:  1.60 m/s
      duration:       9.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 99000
      by:             Transport barge 01 contains: 1000
      to:             KP10_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP09_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 99000
      distance empty: 51249.04 m
      sailing empty:  1.60 m/s
      duration:       8.90 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 90000
      by:             Transport barge 02 contains: 1000
      to:             KP11_clay contains: 4000
      distance full:  50509.98 m
      sailing full:   1.00 m/s
      duration:       14.03 hrs
      distance full:  14146.78 m
      sailing full:   1.00 m/s
      duration:       3.93 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 99000
    T=7056000.00 Condition: Site_KP12_clay.container.level<5000 and Site_KP11_clay.container.level==5000 is satisfied
    T=7056000.00 Condition: Site_KP12_clay.container.level<5000 and Site_KP11_clay.container.level==5000 is satisfied
    T=7056000.00 Condition: Site_KP11_sand.container.level<5000 and Site_KP10_sand.container.level==5000 and Site_KP11_clay.container.level==5000 is satisfied
    T=7056000.00 Clay placement to KP12_clay started
    T=7056000.00 Clay placement to KP12_clay started
    T=7056000.00 Sand placement to KP11_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 94000
      by:             Hopper contains: 1000
      to:             KP11_sand contains: 0
      distance full:  7885.06 m
      sailing full:   1.50 m/s
      duration:       1.46 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP11_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 94000
      distance empty: 7885.06 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 93000
      by:             Hopper contains: 1000
      to:             KP11_sand contains: 1000
      distance full:  7885.06 m
      sailing full:   1.50 m/s
      duration:       1.46 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP11_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 93000
      process:        5.56 hrs
    Unloaded:
      from:           KP11_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 90000
      distance empty: 7885.06 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 92000
      by:             Hopper contains: 1000
      to:             KP11_sand contains: 2000
      distance full:  7885.06 m
      sailing full:   1.50 m/s
      duration:       1.46 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP11_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 92000
      distance empty: 14146.78 m
      sailing empty:  1.60 m/s
      duration:       2.46 hrs
      distance empty: 7885.06 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      distance empty: 50509.98 m
      sailing empty:  1.60 m/s
      duration:       8.77 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 91000
      by:             Hopper contains: 1000
      to:             KP11_sand contains: 3000
      distance full:  7885.06 m
      sailing full:   1.50 m/s
      duration:       1.46 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP11_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 91000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 107000
      by:             Transport barge 02 contains: 1000
      to:             KP08_levvel contains: 2000
      distance empty: 7885.06 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 90000
      by:             Hopper contains: 1000
      to:             KP11_sand contains: 4000
      distance full:  7885.06 m
      sailing full:   1.50 m/s
      duration:       1.46 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP11_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 90000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 106000
      by:             Transport barge 01 contains: 1000
      to:             KP08_levvel contains: 2000
      distance empty: 7885.06 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      distance full:  52221.59 m
      sailing full:   1.00 m/s
      duration:       14.51 hrs
      distance full:  52221.59 m
      sailing full:   1.00 m/s
      duration:       14.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP08_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 106000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 106000
      distance empty: 52221.59 m
      sailing empty:  1.60 m/s
      duration:       9.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 98000
      by:             Transport barge 02 contains: 1000
      to:             KP10_armour contains: 1000
      distance empty: 52221.59 m
      sailing empty:  1.60 m/s
      duration:       9.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 89000
      by:             Transport barge 01 contains: 1000
      to:             KP12_clay contains: 0
      distance full:  15264.94 m
      sailing full:   1.00 m/s
      duration:       4.24 hrs
      distance full:  50509.98 m
      sailing full:   1.00 m/s
      duration:       14.03 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 89000
      distance empty: 15264.94 m
      sailing empty:  1.60 m/s
      duration:       2.65 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 97000
      by:             Transport barge 01 contains: 1000
      to:             KP10_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP10_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 97000
      distance empty: 50509.98 m
      sailing empty:  1.60 m/s
      duration:       8.77 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 88000
      by:             Transport barge 02 contains: 1000
      to:             KP12_clay contains: 1000
      distance full:  50509.98 m
      sailing full:   1.00 m/s
      duration:       14.03 hrs
      distance full:  15264.94 m
      sailing full:   1.00 m/s
      duration:       4.24 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 97000
      process:        5.56 hrs
    Unloaded:
      from:           KP12_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 88000
      distance empty: 15264.94 m
      sailing empty:  1.60 m/s
      duration:       2.65 hrs
      distance empty: 50509.98 m
      sailing empty:  1.60 m/s
      duration:       8.77 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 105000
      by:             Transport barge 02 contains: 1000
      to:             KP08_levvel contains: 4000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 87000
      by:             Transport barge 01 contains: 1000
      to:             KP12_clay contains: 2000
      distance full:  15264.94 m
      sailing full:   1.00 m/s
      duration:       4.24 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 87000
      distance full:  52221.59 m
      sailing full:   1.00 m/s
      duration:       14.51 hrs
    T=7448400.00 Condition: Site_KP09_levvel.container.level<5000 and Site_KP08_levvel.container.level==5000 and Site_KP09_armour.container.level==5000 is satisfied
    T=7448400.00 Condition: Site_KP09_levvel.container.level<5000 and Site_KP08_levvel.container.level==5000 and Site_KP09_armour.container.level==5000 is satisfied
    T=7448400.00 Block placement to KP09_levvel started
    T=7448400.00 Block placement to KP09_levvel started
      distance empty: 15264.94 m
      sailing empty:  1.60 m/s
      duration:       2.65 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 96000
      by:             Transport barge 01 contains: 1000
      to:             KP10_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP08_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 105000
      distance empty: 52221.59 m
      sailing empty:  1.60 m/s
      duration:       9.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 95000
      by:             Transport barge 02 contains: 1000
      to:             KP10_armour contains: 3000
      distance full:  50509.98 m
      sailing full:   1.00 m/s
      duration:       14.03 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 95000
      distance full:  50509.98 m
      sailing full:   1.00 m/s
      duration:       14.03 hrs
    T=7560000.00 Condition: Site_KP11_armour.container.level<5000 and Site_KP10_armour.container.level==5000 and Site_KP11_sand.container.level==5000 is satisfied
    T=7560000.00 Condition: Site_KP11_armour.container.level<5000 and Site_KP10_armour.container.level==5000 and Site_KP11_sand.container.level==5000 is satisfied
    T=7560000.00 Armour placement to KP11_armour started
    T=7560000.00 Armour placement to KP11_armour started
      distance empty: 50509.98 m
      sailing empty:  1.60 m/s
      duration:       8.77 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 104000
      by:             Transport barge 01 contains: 1000
      to:             KP09_levvel contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP10_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 95000
      distance empty: 50509.98 m
      sailing empty:  1.60 m/s
      duration:       8.77 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 86000
      by:             Transport barge 02 contains: 1000
      to:             KP12_clay contains: 3000
      distance full:  51471.36 m
      sailing full:   1.00 m/s
      duration:       14.30 hrs
      distance full:  15264.94 m
      sailing full:   1.00 m/s
      duration:       4.24 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 104000
      process:        5.56 hrs
    Unloaded:
      from:           KP12_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 86000
      distance empty: 15264.94 m
      sailing empty:  1.60 m/s
      duration:       2.65 hrs
      distance empty: 51471.36 m
      sailing empty:  1.60 m/s
      duration:       8.94 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 103000
      by:             Transport barge 02 contains: 1000
      to:             KP09_levvel contains: 1000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 85000
      by:             Transport barge 01 contains: 1000
      to:             KP12_clay contains: 4000
      distance full:  15264.94 m
      sailing full:   1.00 m/s
      duration:       4.24 hrs
    T=7707600.00 Condition: Site_KP13_clay.container.level<5000 and Site_KP12_clay.container.level==5000 is satisfied
    T=7707600.00 Condition: Site_KP13_clay.container.level<5000 and Site_KP12_clay.container.level==5000 is satisfied
    T=7707600.00 Condition: Site_KP12_sand.container.level<5000 and Site_KP11_sand.container.level==5000 and Site_KP12_clay.container.level==5000 is satisfied
    T=7707600.00 Clay placement to KP13_clay started
    T=7707600.00 Clay placement to KP13_clay started
    T=7707600.00 Sand placement to KP12_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 89000
      by:             Hopper contains: 1000
      to:             KP12_sand contains: 0
      distance full:  7925.88 m
      sailing full:   1.50 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP12_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 89000
      distance empty: 7925.88 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 88000
      by:             Hopper contains: 1000
      to:             KP12_sand contains: 1000
      distance full:  7925.88 m
      sailing full:   1.50 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP12_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 88000
      process:        5.56 hrs
    Unloaded:
      from:           KP12_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 85000
      distance empty: 7925.88 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 87000
      by:             Hopper contains: 1000
      to:             KP12_sand contains: 2000
      distance full:  51471.36 m
      sailing full:   1.00 m/s
      duration:       14.30 hrs
      distance full:  7925.88 m
      sailing full:   1.50 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP12_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 87000
      distance empty: 15264.94 m
      sailing empty:  1.60 m/s
      duration:       2.65 hrs
      distance empty: 7925.88 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 86000
      by:             Hopper contains: 1000
      to:             KP12_sand contains: 3000
      distance full:  7925.88 m
      sailing full:   1.50 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP12_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 86000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 94000
      by:             Transport barge 01 contains: 1000
      to:             KP11_armour contains: 0
      distance empty: 7925.88 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 85000
      by:             Hopper contains: 1000
      to:             KP12_sand contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 103000
      distance full:  7925.88 m
      sailing full:   1.50 m/s
      duration:       1.47 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP12_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 85000
      distance empty: 7925.88 m
      sailing empty:  2.00 m/s
      duration:       1.10 hrs
      distance empty: 51471.36 m
      sailing empty:  1.60 m/s
      duration:       8.94 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 93000
      by:             Transport barge 02 contains: 1000
      to:             KP11_armour contains: 0
      distance full:  49785.75 m
      sailing full:   1.00 m/s
      duration:       13.83 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 93000
      distance full:  49785.75 m
      sailing full:   1.00 m/s
      duration:       13.83 hrs
      distance empty: 49785.75 m
      sailing empty:  1.60 m/s
      duration:       8.64 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 102000
      by:             Transport barge 01 contains: 1000
      to:             KP09_levvel contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP11_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 93000
      distance empty: 49785.75 m
      sailing empty:  1.60 m/s
      duration:       8.64 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 84000
      by:             Transport barge 02 contains: 1000
      to:             KP13_clay contains: 0
      distance full:  51471.36 m
      sailing full:   1.00 m/s
      duration:       14.30 hrs
      distance full:  16384.06 m
      sailing full:   1.00 m/s
      duration:       4.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 102000
      process:        5.56 hrs
    Unloaded:
      from:           KP13_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 84000
      distance empty: 16384.06 m
      sailing empty:  1.60 m/s
      duration:       2.84 hrs
      distance empty: 51471.36 m
      sailing empty:  1.60 m/s
      duration:       8.94 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 101000
      by:             Transport barge 02 contains: 1000
      to:             KP09_levvel contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 83000
      by:             Transport barge 01 contains: 1000
      to:             KP13_clay contains: 1000
      distance full:  16384.06 m
      sailing full:   1.00 m/s
      duration:       4.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 83000
      distance full:  51471.36 m
      sailing full:   1.00 m/s
      duration:       14.30 hrs
      distance empty: 16384.06 m
      sailing empty:  1.60 m/s
      duration:       2.84 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 92000
      by:             Transport barge 01 contains: 1000
      to:             KP11_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP09_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 101000
      distance empty: 51471.36 m
      sailing empty:  1.60 m/s
      duration:       8.94 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 91000
      by:             Transport barge 02 contains: 1000
      to:             KP11_armour contains: 2000
      distance full:  49785.75 m
      sailing full:   1.00 m/s
      duration:       13.83 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 91000
      distance full:  49785.75 m
      sailing full:   1.00 m/s
      duration:       13.83 hrs
      distance empty: 49785.75 m
      sailing empty:  1.60 m/s
      duration:       8.64 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 100000
      by:             Transport barge 01 contains: 1000
      to:             KP09_levvel contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP11_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 91000
      distance empty: 49785.75 m
      sailing empty:  1.60 m/s
      duration:       8.64 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 82000
      by:             Transport barge 02 contains: 1000
      to:             KP13_clay contains: 2000
      distance full:  51471.36 m
      sailing full:   1.00 m/s
      duration:       14.30 hrs
    T=8200800.00 Condition: Site_KP10_levvel.container.level<5000 and Site_KP09_levvel.container.level==5000 and Site_KP10_armour.container.level==5000 is satisfied
    T=8200800.00 Condition: Site_KP10_levvel.container.level<5000 and Site_KP09_levvel.container.level==5000 and Site_KP10_armour.container.level==5000 is satisfied
    T=8200800.00 Block placement to KP10_levvel started
    T=8200800.00 Block placement to KP10_levvel started
      distance full:  16384.06 m
      sailing full:   1.00 m/s
      duration:       4.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP09_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 100000
      process:        5.56 hrs
    Unloaded:
      from:           KP13_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 82000
      distance empty: 16384.06 m
      sailing empty:  1.60 m/s
      duration:       2.84 hrs
      distance empty: 51471.36 m
      sailing empty:  1.60 m/s
      duration:       8.94 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 99000
      by:             Transport barge 02 contains: 1000
      to:             KP10_levvel contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 81000
      by:             Transport barge 01 contains: 1000
      to:             KP13_clay contains: 3000
      distance full:  16384.06 m
      sailing full:   1.00 m/s
      duration:       4.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 81000
      distance full:  50735.39 m
      sailing full:   1.00 m/s
      duration:       14.09 hrs
      distance empty: 16384.06 m
      sailing empty:  1.60 m/s
      duration:       2.84 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 90000
      by:             Transport barge 01 contains: 1000
      to:             KP11_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP10_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 99000
      distance empty: 50735.39 m
      sailing empty:  1.60 m/s
      duration:       8.81 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 80000
      by:             Transport barge 02 contains: 1000
      to:             KP13_clay contains: 4000
      distance full:  49785.75 m
      sailing full:   1.00 m/s
      duration:       13.83 hrs
    T=8377200.00 Condition: Site_KP12_armour.container.level<5000 and Site_KP11_armour.container.level==5000 and Site_KP12_sand.container.level==5000 is satisfied
    T=8377200.00 Condition: Site_KP12_armour.container.level<5000 and Site_KP11_armour.container.level==5000 and Site_KP12_sand.container.level==5000 is satisfied
    T=8377200.00 Armour placement to KP12_armour started
    T=8377200.00 Armour placement to KP12_armour started
      distance full:  16384.06 m
      sailing full:   1.00 m/s
      duration:       4.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 90000
    T=8395200.00 Condition: Site_KP14_clay.container.level<5000 and Site_KP13_clay.container.level==5000 is satisfied
    T=8395200.00 Condition: Site_KP14_clay.container.level<5000 and Site_KP13_clay.container.level==5000 is satisfied
    T=8395200.00 Condition: Site_KP13_sand.container.level<5000 and Site_KP12_sand.container.level==5000 and Site_KP13_clay.container.level==5000 is satisfied
    T=8395200.00 Clay placement to KP14_clay started
    T=8395200.00 Clay placement to KP14_clay started
    T=8395200.00 Sand placement to KP13_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 84000
      by:             Hopper contains: 1000
      to:             KP13_sand contains: 0
      distance full:  8124.59 m
      sailing full:   1.50 m/s
      duration:       1.50 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP13_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 84000
      distance empty: 8124.59 m
      sailing empty:  2.00 m/s
      duration:       1.13 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 83000
      by:             Hopper contains: 1000
      to:             KP13_sand contains: 1000
      distance full:  8124.59 m
      sailing full:   1.50 m/s
      duration:       1.50 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP13_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 83000
      process:        5.56 hrs
    Unloaded:
      from:           KP13_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 80000
      distance empty: 8124.59 m
      sailing empty:  2.00 m/s
      duration:       1.13 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 82000
      by:             Hopper contains: 1000
      to:             KP13_sand contains: 2000
      distance full:  8124.59 m
      sailing full:   1.50 m/s
      duration:       1.50 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP13_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 82000
      distance empty: 16384.06 m
      sailing empty:  1.60 m/s
      duration:       2.84 hrs
      distance empty: 49785.75 m
      sailing empty:  1.60 m/s
      duration:       8.64 hrs
      distance empty: 8124.59 m
      sailing empty:  2.00 m/s
      duration:       1.13 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 81000
      by:             Hopper contains: 1000
      to:             KP13_sand contains: 3000
      distance full:  8124.59 m
      sailing full:   1.50 m/s
      duration:       1.50 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP13_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 81000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 98000
      by:             Transport barge 02 contains: 1000
      to:             KP10_levvel contains: 1000
      distance empty: 8124.59 m
      sailing empty:  2.00 m/s
      duration:       1.13 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 80000
      by:             Hopper contains: 1000
      to:             KP13_sand contains: 4000
      distance full:  8124.59 m
      sailing full:   1.50 m/s
      duration:       1.50 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP13_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 80000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 97000
      by:             Transport barge 01 contains: 1000
      to:             KP10_levvel contains: 1000
      distance empty: 8124.59 m
      sailing empty:  2.00 m/s
      duration:       1.13 hrs
      distance full:  50735.39 m
      sailing full:   1.00 m/s
      duration:       14.09 hrs
      distance full:  50735.39 m
      sailing full:   1.00 m/s
      duration:       14.09 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 97000
      process:        5.56 hrs
    Unloaded:
      from:           KP10_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 97000
      distance empty: 50735.39 m
      sailing empty:  1.60 m/s
      duration:       8.81 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 89000
      by:             Transport barge 02 contains: 1000
      to:             KP12_armour contains: 0
      distance empty: 50735.39 m
      sailing empty:  1.60 m/s
      duration:       8.81 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 88000
      by:             Transport barge 01 contains: 1000
      to:             KP12_armour contains: 0
      distance full:  49076.97 m
      sailing full:   1.00 m/s
      duration:       13.63 hrs
      distance full:  49076.97 m
      sailing full:   1.00 m/s
      duration:       13.63 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 88000
      process:        5.56 hrs
    Unloaded:
      from:           KP12_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 88000
      distance empty: 49076.97 m
      sailing empty:  1.60 m/s
      duration:       8.52 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 79000
      by:             Transport barge 02 contains: 1000
      to:             KP14_clay contains: 0
      distance empty: 49076.97 m
      sailing empty:  1.60 m/s
      duration:       8.52 hrs
      distance full:  17503.96 m
      sailing full:   1.00 m/s
      duration:       4.86 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 78000
      by:             Transport barge 01 contains: 1000
      to:             KP14_clay contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 78000
      distance full:  17503.96 m
      sailing full:   1.00 m/s
      duration:       4.86 hrs
      distance empty: 17503.96 m
      sailing empty:  1.60 m/s
      duration:       3.04 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 78000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 96000
      by:             Transport barge 02 contains: 1000
      to:             KP10_levvel contains: 3000
      distance empty: 17503.96 m
      sailing empty:  1.60 m/s
      duration:       3.04 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 95000
      by:             Transport barge 01 contains: 1000
      to:             KP10_levvel contains: 3000
      distance full:  50735.39 m
      sailing full:   1.00 m/s
      duration:       14.09 hrs
      distance full:  50735.39 m
      sailing full:   1.00 m/s
      duration:       14.09 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP10_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 95000
    T=8787600.00 Condition: Site_KP11_levvel.container.level<5000 and Site_KP10_levvel.container.level==5000 and Site_KP11_armour.container.level==5000 is satisfied
    T=8787600.00 Condition: Site_KP11_levvel.container.level<5000 and Site_KP10_levvel.container.level==5000 and Site_KP11_armour.container.level==5000 is satisfied
    T=8787600.00 Block placement to KP11_levvel started
    T=8787600.00 Block placement to KP11_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP10_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 95000
      distance empty: 50735.39 m
      sailing empty:  1.60 m/s
      duration:       8.81 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 87000
      by:             Transport barge 02 contains: 1000
      to:             KP12_armour contains: 2000
      distance empty: 50735.39 m
      sailing empty:  1.60 m/s
      duration:       8.81 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 86000
      by:             Transport barge 01 contains: 1000
      to:             KP12_armour contains: 2000
      distance full:  49076.97 m
      sailing full:   1.00 m/s
      duration:       13.63 hrs
      distance full:  49076.97 m
      sailing full:   1.00 m/s
      duration:       13.63 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 86000
      process:        5.56 hrs
    Unloaded:
      from:           KP12_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 86000
      distance empty: 49076.97 m
      sailing empty:  1.60 m/s
      duration:       8.52 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 77000
      by:             Transport barge 02 contains: 1000
      to:             KP14_clay contains: 2000
      distance empty: 49076.97 m
      sailing empty:  1.60 m/s
      duration:       8.52 hrs
      distance full:  17503.96 m
      sailing full:   1.00 m/s
      duration:       4.86 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 76000
      by:             Transport barge 01 contains: 1000
      to:             KP14_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 76000
      distance full:  17503.96 m
      sailing full:   1.00 m/s
      duration:       4.86 hrs
      distance empty: 17503.96 m
      sailing empty:  1.60 m/s
      duration:       3.04 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 76000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 94000
      by:             Transport barge 02 contains: 1000
      to:             KP11_levvel contains: 0
      distance empty: 17503.96 m
      sailing empty:  1.60 m/s
      duration:       3.04 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 93000
      by:             Transport barge 01 contains: 1000
      to:             KP11_levvel contains: 0
      distance full:  50014.32 m
      sailing full:   1.00 m/s
      duration:       13.89 hrs
      distance full:  50014.32 m
      sailing full:   1.00 m/s
      duration:       13.89 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 93000
      process:        5.56 hrs
    Unloaded:
      from:           KP11_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 93000
      distance empty: 50014.32 m
      sailing empty:  1.60 m/s
      duration:       8.68 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 85000
      by:             Transport barge 02 contains: 1000
      to:             KP12_armour contains: 4000
      distance empty: 50014.32 m
      sailing empty:  1.60 m/s
      duration:       8.68 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 92000
      by:             Transport barge 01 contains: 1000
      to:             KP11_levvel contains: 2000
      distance full:  49076.97 m
      sailing full:   1.00 m/s
      duration:       13.63 hrs
    T=9158400.00 Condition: Site_KP13_armour.container.level<5000 and Site_KP12_armour.container.level==5000 and Site_KP13_sand.container.level==5000 is satisfied
    T=9158400.00 Condition: Site_KP13_armour.container.level<5000 and Site_KP12_armour.container.level==5000 and Site_KP13_sand.container.level==5000 is satisfied
    T=9158400.00 Armour placement to KP13_armour started
    T=9158400.00 Armour placement to KP13_armour started
      process:        5.56 hrs
    Unloaded:
      from:           KP12_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 85000
      distance full:  50014.32 m
      sailing full:   1.00 m/s
      duration:       13.89 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 92000
      distance empty: 49076.97 m
      sailing empty:  1.60 m/s
      duration:       8.52 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 75000
      by:             Transport barge 02 contains: 1000
      to:             KP14_clay contains: 4000
      distance empty: 50014.32 m
      sailing empty:  1.60 m/s
      duration:       8.68 hrs
      distance full:  17503.96 m
      sailing full:   1.00 m/s
      duration:       4.86 hrs
    T=9237600.00 Condition: Site_KP15_clay.container.level<5000 and Site_KP14_clay.container.level==5000 is satisfied
    T=9237600.00 Condition: Site_KP15_clay.container.level<5000 and Site_KP14_clay.container.level==5000 is satisfied
    T=9237600.00 Condition: Site_KP14_sand.container.level<5000 and Site_KP13_sand.container.level==5000 and Site_KP14_clay.container.level==5000 is satisfied
    T=9237600.00 Clay placement to KP15_clay started
    T=9237600.00 Clay placement to KP15_clay started
    T=9237600.00 Sand placement to KP14_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 79000
      by:             Hopper contains: 1000
      to:             KP14_sand contains: 0
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 84000
      by:             Transport barge 01 contains: 1000
      to:             KP13_armour contains: 0
      distance full:  8470.07 m
      sailing full:   1.50 m/s
      duration:       1.57 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP14_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 79000
      distance empty: 8470.07 m
      sailing empty:  2.00 m/s
      duration:       1.18 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 78000
      by:             Hopper contains: 1000
      to:             KP14_sand contains: 1000
      distance full:  8470.07 m
      sailing full:   1.50 m/s
      duration:       1.57 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 75000
      process:        0.14 hrs
    Unloaded:
      from:           KP14_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 78000
      distance empty: 8470.07 m
      sailing empty:  2.00 m/s
      duration:       1.18 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 77000
      by:             Hopper contains: 1000
      to:             KP14_sand contains: 2000
      distance full:  8470.07 m
      sailing full:   1.50 m/s
      duration:       1.57 hrs
      distance empty: 17503.96 m
      sailing empty:  1.60 m/s
      duration:       3.04 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP14_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 77000
      distance empty: 8470.07 m
      sailing empty:  2.00 m/s
      duration:       1.18 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 76000
      by:             Hopper contains: 1000
      to:             KP14_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 91000
      by:             Transport barge 02 contains: 1000
      to:             KP11_levvel contains: 3000
      distance full:  8470.07 m
      sailing full:   1.50 m/s
      duration:       1.57 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP14_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 76000
      distance empty: 8470.07 m
      sailing empty:  2.00 m/s
      duration:       1.18 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 75000
      by:             Hopper contains: 1000
      to:             KP14_sand contains: 4000
      distance full:  48384.33 m
      sailing full:   1.00 m/s
      duration:       13.44 hrs
      distance full:  8470.07 m
      sailing full:   1.50 m/s
      duration:       1.57 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP14_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 75000
      distance empty: 8470.07 m
      sailing empty:  2.00 m/s
      duration:       1.18 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 84000
      distance full:  50014.32 m
      sailing full:   1.00 m/s
      duration:       13.89 hrs
      distance empty: 48384.33 m
      sailing empty:  1.60 m/s
      duration:       8.40 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP11_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 90000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 90000
      by:             Transport barge 01 contains: 1000
      to:             KP11_levvel contains: 4000
      distance empty: 50014.32 m
      sailing empty:  1.60 m/s
      duration:       8.68 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 83000
      by:             Transport barge 02 contains: 1000
      to:             KP13_armour contains: 1000
      distance full:  50014.32 m
      sailing full:   1.00 m/s
      duration:       13.89 hrs
    T=9399600.00 Condition: Site_KP12_levvel.container.level<5000 and Site_KP11_levvel.container.level==5000 and Site_KP12_armour.container.level==5000 is satisfied
    T=9399600.00 Condition: Site_KP12_levvel.container.level<5000 and Site_KP11_levvel.container.level==5000 and Site_KP12_armour.container.level==5000 is satisfied
    T=9399600.00 Block placement to KP12_levvel started
    T=9399600.00 Block placement to KP12_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP11_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 90000
      distance full:  48384.33 m
      sailing full:   1.00 m/s
      duration:       13.44 hrs
      distance empty: 50014.32 m
      sailing empty:  1.60 m/s
      duration:       8.68 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 83000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 74000
      by:             Transport barge 01 contains: 1000
      to:             KP15_clay contains: 0
      distance full:  18624.46 m
      sailing full:   1.00 m/s
      duration:       5.17 hrs
      distance empty: 48384.33 m
      sailing empty:  1.60 m/s
      duration:       8.40 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 73000
      by:             Transport barge 02 contains: 1000
      to:             KP15_clay contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 73000
      distance empty: 18624.46 m
      sailing empty:  1.60 m/s
      duration:       3.23 hrs
      distance full:  18624.46 m
      sailing full:   1.00 m/s
      duration:       5.17 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 82000
      by:             Transport barge 01 contains: 1000
      to:             KP13_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_clay contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 73000
      distance empty: 18624.46 m
      sailing empty:  1.60 m/s
      duration:       3.23 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 89000
      by:             Transport barge 02 contains: 1000
      to:             KP12_levvel contains: 0
      distance full:  48384.33 m
      sailing full:   1.00 m/s
      duration:       13.44 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 82000
      distance full:  49308.78 m
      sailing full:   1.00 m/s
      duration:       13.70 hrs
      distance empty: 48384.33 m
      sailing empty:  1.60 m/s
      duration:       8.40 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 88000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 88000
      by:             Transport barge 01 contains: 1000
      to:             KP12_levvel contains: 1000
      distance empty: 49308.78 m
      sailing empty:  1.60 m/s
      duration:       8.56 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 81000
      by:             Transport barge 02 contains: 1000
      to:             KP13_armour contains: 3000
      distance full:  49308.78 m
      sailing full:   1.00 m/s
      duration:       13.70 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 88000
      distance full:  48384.33 m
      sailing full:   1.00 m/s
      duration:       13.44 hrs
      distance empty: 49308.78 m
      sailing empty:  1.60 m/s
      duration:       8.56 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 81000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 72000
      by:             Transport barge 01 contains: 1000
      to:             KP15_clay contains: 2000
      distance full:  18624.46 m
      sailing full:   1.00 m/s
      duration:       5.17 hrs
      distance empty: 48384.33 m
      sailing empty:  1.60 m/s
      duration:       8.40 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 71000
      by:             Transport barge 02 contains: 1000
      to:             KP15_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 71000
      distance empty: 18624.46 m
      sailing empty:  1.60 m/s
      duration:       3.23 hrs
      distance full:  18624.46 m
      sailing full:   1.00 m/s
      duration:       5.17 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 80000
      by:             Transport barge 01 contains: 1000
      to:             KP13_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 71000
      distance empty: 18624.46 m
      sailing empty:  1.60 m/s
      duration:       3.23 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 87000
      by:             Transport barge 02 contains: 1000
      to:             KP12_levvel contains: 2000
      distance full:  48384.33 m
      sailing full:   1.00 m/s
      duration:       13.44 hrs
    T=9849600.00 Condition: Site_KP14_armour.container.level<5000 and Site_KP13_armour.container.level==5000 and Site_KP14_sand.container.level==5000 is satisfied
    T=9849600.00 Condition: Site_KP14_armour.container.level<5000 and Site_KP13_armour.container.level==5000 and Site_KP14_sand.container.level==5000 is satisfied
    T=9849600.00 Armour placement to KP14_armour started
    T=9849600.00 Armour placement to KP14_armour started
      process:        5.56 hrs
    Unloaded:
      from:           KP13_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 80000
      distance full:  49308.78 m
      sailing full:   1.00 m/s
      duration:       13.70 hrs
      distance empty: 48384.33 m
      sailing empty:  1.60 m/s
      duration:       8.40 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 86000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 86000
      by:             Transport barge 01 contains: 1000
      to:             KP12_levvel contains: 3000
      distance empty: 49308.78 m
      sailing empty:  1.60 m/s
      duration:       8.56 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 79000
      by:             Transport barge 02 contains: 1000
      to:             KP14_armour contains: 0
      distance full:  49308.78 m
      sailing full:   1.00 m/s
      duration:       13.70 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP12_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 86000
      distance full:  47708.52 m
      sailing full:   1.00 m/s
      duration:       13.25 hrs
      distance empty: 49308.78 m
      sailing empty:  1.60 m/s
      duration:       8.56 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 79000
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 70000
      by:             Transport barge 01 contains: 1000
      to:             KP15_clay contains: 4000
      distance full:  18624.46 m
      sailing full:   1.00 m/s
      duration:       5.17 hrs
    T=10036800.00 Condition: Site_KP16_clay.container.level<5000 and Site_KP15_clay.container.level==5000 is satisfied
    T=10036800.00 Condition: Site_KP16_clay.container.level<5000 and Site_KP15_clay.container.level==5000 is satisfied
    T=10036800.00 Condition: Site_KP15_sand.container.level<5000 and Site_KP14_sand.container.level==5000 and Site_KP15_clay.container.level==5000 is satisfied
    T=10036800.00 Clay placement to KP16_clay started
    T=10036800.00 Clay placement to KP16_clay started
    T=10036800.00 Sand placement to KP15_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 74000
      by:             Hopper contains: 1000
      to:             KP15_sand contains: 0
      distance empty: 47708.52 m
      sailing empty:  1.60 m/s
      duration:       8.28 hrs
      distance full:  8945.28 m
      sailing full:   1.50 m/s
      duration:       1.66 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP15_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 74000
      distance empty: 8945.28 m
      sailing empty:  2.00 m/s
      duration:       1.24 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 73000
      by:             Hopper contains: 1000
      to:             KP15_sand contains: 1000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 85000
      by:             Transport barge 02 contains: 1000
      to:             KP12_levvel contains: 4000
      distance full:  8945.28 m
      sailing full:   1.50 m/s
      duration:       1.66 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP15_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 73000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 70000
      distance empty: 8945.28 m
      sailing empty:  2.00 m/s
      duration:       1.24 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 72000
      by:             Hopper contains: 1000
      to:             KP15_sand contains: 2000
      distance full:  8945.28 m
      sailing full:   1.50 m/s
      duration:       1.66 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP15_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 72000
      distance empty: 18624.46 m
      sailing empty:  1.60 m/s
      duration:       3.23 hrs
      distance empty: 8945.28 m
      sailing empty:  2.00 m/s
      duration:       1.24 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 71000
      by:             Hopper contains: 1000
      to:             KP15_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 78000
      by:             Transport barge 01 contains: 1000
      to:             KP14_armour contains: 1000
      distance full:  8945.28 m
      sailing full:   1.50 m/s
      duration:       1.66 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP15_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 71000
      distance empty: 8945.28 m
      sailing empty:  2.00 m/s
      duration:       1.24 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 70000
      by:             Hopper contains: 1000
      to:             KP15_sand contains: 4000
      distance full:  8945.28 m
      sailing full:   1.50 m/s
      duration:       1.66 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP15_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 70000
      distance empty: 8945.28 m
      sailing empty:  2.00 m/s
      duration:       1.24 hrs
      distance full:  49308.78 m
      sailing full:   1.00 m/s
      duration:       13.70 hrs
    T=10105200.00 Condition: Site_KP13_levvel.container.level<5000 and Site_KP12_levvel.container.level==5000 and Site_KP13_armour.container.level==5000 is satisfied
    T=10105200.00 Condition: Site_KP13_levvel.container.level<5000 and Site_KP12_levvel.container.level==5000 and Site_KP13_armour.container.level==5000 is satisfied
    T=10105200.00 Block placement to KP13_levvel started
    T=10105200.00 Block placement to KP13_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP12_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 85000
      distance full:  47708.52 m
      sailing full:   1.00 m/s
      duration:       13.25 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 78000
      distance empty: 49308.78 m
      sailing empty:  1.60 m/s
      duration:       8.56 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 69000
      by:             Transport barge 02 contains: 1000
      to:             KP16_clay contains: 0
      distance empty: 47708.52 m
      sailing empty:  1.60 m/s
      duration:       8.28 hrs
      distance full:  19745.46 m
      sailing full:   1.00 m/s
      duration:       5.48 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 68000
      by:             Transport barge 01 contains: 1000
      to:             KP16_clay contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 68000
      distance full:  19745.46 m
      sailing full:   1.00 m/s
      duration:       5.48 hrs
      distance empty: 19745.46 m
      sailing empty:  1.60 m/s
      duration:       3.43 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP16_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 68000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 77000
      by:             Transport barge 02 contains: 1000
      to:             KP14_armour contains: 2000
      distance empty: 19745.46 m
      sailing empty:  1.60 m/s
      duration:       3.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 84000
      by:             Transport barge 01 contains: 1000
      to:             KP13_levvel contains: 0
      distance full:  47708.52 m
      sailing full:   1.00 m/s
      duration:       13.25 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 77000
      distance full:  48619.46 m
      sailing full:   1.00 m/s
      duration:       13.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 84000
      distance empty: 47708.52 m
      sailing empty:  1.60 m/s
      duration:       8.28 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 83000
      by:             Transport barge 02 contains: 1000
      to:             KP13_levvel contains: 1000
      distance empty: 48619.46 m
      sailing empty:  1.60 m/s
      duration:       8.44 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 76000
      by:             Transport barge 01 contains: 1000
      to:             KP14_armour contains: 3000
      distance full:  48619.46 m
      sailing full:   1.00 m/s
      duration:       13.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 83000
      distance full:  47708.52 m
      sailing full:   1.00 m/s
      duration:       13.25 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP14_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 76000
      distance empty: 48619.46 m
      sailing empty:  1.60 m/s
      duration:       8.44 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 67000
      by:             Transport barge 02 contains: 1000
      to:             KP16_clay contains: 2000
      distance empty: 47708.52 m
      sailing empty:  1.60 m/s
      duration:       8.28 hrs
      distance full:  19745.46 m
      sailing full:   1.00 m/s
      duration:       5.48 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 66000
      by:             Transport barge 01 contains: 1000
      to:             KP16_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 66000
      distance full:  19745.46 m
      sailing full:   1.00 m/s
      duration:       5.48 hrs
      distance empty: 19745.46 m
      sailing empty:  1.60 m/s
      duration:       3.43 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP16_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 66000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 75000
      by:             Transport barge 02 contains: 1000
      to:             KP14_armour contains: 4000
      distance empty: 19745.46 m
      sailing empty:  1.60 m/s
      duration:       3.43 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 82000
      by:             Transport barge 01 contains: 1000
      to:             KP13_levvel contains: 2000
      distance full:  47708.52 m
      sailing full:   1.00 m/s
      duration:       13.25 hrs
    T=10551600.00 Condition: Site_KP15_armour.container.level<5000 and Site_KP14_armour.container.level==5000 and Site_KP15_sand.container.level==5000 is satisfied
    T=10551600.00 Condition: Site_KP15_armour.container.level<5000 and Site_KP14_armour.container.level==5000 and Site_KP15_sand.container.level==5000 is satisfied
    T=10551600.00 Armour placement to KP15_armour started
    T=10551600.00 Armour placement to KP15_armour started
      process:        5.56 hrs
    Unloaded:
      from:           KP14_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 75000
      distance full:  48619.46 m
      sailing full:   1.00 m/s
      duration:       13.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 82000
      distance empty: 47708.52 m
      sailing empty:  1.60 m/s
      duration:       8.28 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 81000
      by:             Transport barge 02 contains: 1000
      to:             KP13_levvel contains: 3000
      distance empty: 48619.46 m
      sailing empty:  1.60 m/s
      duration:       8.44 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 74000
      by:             Transport barge 01 contains: 1000
      to:             KP15_armour contains: 0
      distance full:  48619.46 m
      sailing full:   1.00 m/s
      duration:       13.51 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 81000
      distance full:  47050.25 m
      sailing full:   1.00 m/s
      duration:       13.07 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP15_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 74000
      distance empty: 48619.46 m
      sailing empty:  1.60 m/s
      duration:       8.44 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 65000
      by:             Transport barge 02 contains: 1000
      to:             KP16_clay contains: 4000
      distance empty: 47050.25 m
      sailing empty:  1.60 m/s
      duration:       8.17 hrs
      distance full:  19745.46 m
      sailing full:   1.00 m/s
      duration:       5.48 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 80000
      by:             Transport barge 01 contains: 1000
      to:             KP13_levvel contains: 4000
    T=10742400.00 Condition: Site_KP17_clay.container.level<5000 and Site_KP16_clay.container.level==5000 is satisfied
    T=10742400.00 Condition: Site_KP17_clay.container.level<5000 and Site_KP16_clay.container.level==5000 is satisfied
    T=10742400.00 Condition: Site_KP16_sand.container.level<5000 and Site_KP15_sand.container.level==5000 and Site_KP16_clay.container.level==5000 is satisfied
    T=10742400.00 Clay placement to KP17_clay started
    T=10742400.00 Clay placement to KP17_clay started
    T=10742400.00 Sand placement to KP16_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 69000
      by:             Hopper contains: 1000
      to:             KP16_sand contains: 0
      distance full:  9530.80 m
      sailing full:   1.50 m/s
      duration:       1.76 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP16_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 69000
      distance empty: 9530.80 m
      sailing empty:  2.00 m/s
      duration:       1.32 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 68000
      by:             Hopper contains: 1000
      to:             KP16_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 65000
      distance full:  9530.80 m
      sailing full:   1.50 m/s
      duration:       1.76 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP16_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 68000
      distance empty: 9530.80 m
      sailing empty:  2.00 m/s
      duration:       1.32 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 67000
      by:             Hopper contains: 1000
      to:             KP16_sand contains: 2000
      distance empty: 19745.46 m
      sailing empty:  1.60 m/s
      duration:       3.43 hrs
      distance full:  9530.80 m
      sailing full:   1.50 m/s
      duration:       1.76 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP16_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 67000
      distance empty: 9530.80 m
      sailing empty:  2.00 m/s
      duration:       1.32 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 66000
      by:             Hopper contains: 1000
      to:             KP16_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 73000
      by:             Transport barge 02 contains: 1000
      to:             KP15_armour contains: 1000
      distance full:  9530.80 m
      sailing full:   1.50 m/s
      duration:       1.76 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP16_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 66000
      distance full:  48619.46 m
      sailing full:   1.00 m/s
      duration:       13.51 hrs
      distance empty: 9530.80 m
      sailing empty:  2.00 m/s
      duration:       1.32 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 65000
      by:             Hopper contains: 1000
      to:             KP16_sand contains: 4000
    T=10792800.00 Condition: Site_KP14_levvel.container.level<5000 and Site_KP13_levvel.container.level==5000 and Site_KP14_armour.container.level==5000 is satisfied
    T=10792800.00 Condition: Site_KP14_levvel.container.level<5000 and Site_KP13_levvel.container.level==5000 and Site_KP14_armour.container.level==5000 is satisfied
    T=10792800.00 Block placement to KP14_levvel started
    T=10792800.00 Block placement to KP14_levvel started
      distance full:  9530.80 m
      sailing full:   1.50 m/s
      duration:       1.76 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP16_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 65000
      distance empty: 9530.80 m
      sailing empty:  2.00 m/s
      duration:       1.32 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP13_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 80000
      distance full:  47050.25 m
      sailing full:   1.00 m/s
      duration:       13.07 hrs
      distance empty: 48619.46 m
      sailing empty:  1.60 m/s
      duration:       8.44 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP15_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 72000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 72000
      by:             Transport barge 01 contains: 1000
      to:             KP15_armour contains: 2000
      distance empty: 47050.25 m
      sailing empty:  1.60 m/s
      duration:       8.17 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 64000
      by:             Transport barge 02 contains: 1000
      to:             KP17_clay contains: 0
      distance full:  47050.25 m
      sailing full:   1.00 m/s
      duration:       13.07 hrs
      distance full:  20866.85 m
      sailing full:   1.00 m/s
      duration:       5.80 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP15_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 72000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 64000
      distance empty: 47050.25 m
      sailing empty:  1.60 m/s
      duration:       8.17 hrs
      distance empty: 20866.85 m
      sailing empty:  1.60 m/s
      duration:       3.62 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 63000
      by:             Transport barge 01 contains: 1000
      to:             KP17_clay contains: 1000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 79000
      by:             Transport barge 02 contains: 1000
      to:             KP14_levvel contains: 0
      distance full:  20866.85 m
      sailing full:   1.00 m/s
      duration:       5.80 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 63000
      distance empty: 20866.85 m
      sailing empty:  1.60 m/s
      duration:       3.62 hrs
      distance full:  47947.03 m
      sailing full:   1.00 m/s
      duration:       13.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 78000
      by:             Transport barge 01 contains: 1000
      to:             KP14_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 78000
      distance empty: 47947.03 m
      sailing empty:  1.60 m/s
      duration:       8.32 hrs
      distance full:  47947.03 m
      sailing full:   1.00 m/s
      duration:       13.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 71000
      by:             Transport barge 02 contains: 1000
      to:             KP15_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 78000
      distance empty: 47947.03 m
      sailing empty:  1.60 m/s
      duration:       8.32 hrs
      distance full:  47050.25 m
      sailing full:   1.00 m/s
      duration:       13.07 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 70000
      by:             Transport barge 01 contains: 1000
      to:             KP15_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 70000
      distance empty: 47050.25 m
      sailing empty:  1.60 m/s
      duration:       8.17 hrs
      distance full:  47050.25 m
      sailing full:   1.00 m/s
      duration:       13.07 hrs
    T=11178000.00 Condition: Site_KP16_armour.container.level<5000 and Site_KP15_armour.container.level==5000 and Site_KP16_sand.container.level==5000 is satisfied
    T=11178000.00 Condition: Site_KP16_armour.container.level<5000 and Site_KP15_armour.container.level==5000 and Site_KP16_sand.container.level==5000 is satisfied
    T=11178000.00 Armour placement to KP16_armour started
    T=11178000.00 Armour placement to KP16_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 62000
      by:             Transport barge 02 contains: 1000
      to:             KP17_clay contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 70000
      distance full:  20866.85 m
      sailing full:   1.00 m/s
      duration:       5.80 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 62000
      distance empty: 47050.25 m
      sailing empty:  1.60 m/s
      duration:       8.17 hrs
      distance empty: 20866.85 m
      sailing empty:  1.60 m/s
      duration:       3.62 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 61000
      by:             Transport barge 01 contains: 1000
      to:             KP17_clay contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 77000
      by:             Transport barge 02 contains: 1000
      to:             KP14_levvel contains: 2000
      distance full:  20866.85 m
      sailing full:   1.00 m/s
      duration:       5.80 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_clay contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 61000
      distance empty: 20866.85 m
      sailing empty:  1.60 m/s
      duration:       3.62 hrs
      distance full:  47947.03 m
      sailing full:   1.00 m/s
      duration:       13.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 76000
      by:             Transport barge 01 contains: 1000
      to:             KP14_levvel contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 76000
      distance empty: 47947.03 m
      sailing empty:  1.60 m/s
      duration:       8.32 hrs
      distance full:  47947.03 m
      sailing full:   1.00 m/s
      duration:       13.32 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 69000
      by:             Transport barge 02 contains: 1000
      to:             KP16_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP14_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 76000
      distance empty: 47947.03 m
      sailing empty:  1.60 m/s
      duration:       8.32 hrs
      distance full:  46410.28 m
      sailing full:   1.00 m/s
      duration:       12.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 68000
      by:             Transport barge 01 contains: 1000
      to:             KP16_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 68000
      distance empty: 46410.28 m
      sailing empty:  1.60 m/s
      duration:       8.06 hrs
      distance full:  46410.28 m
      sailing full:   1.00 m/s
      duration:       12.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 60000
      by:             Transport barge 02 contains: 1000
      to:             KP17_clay contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 68000
      distance full:  20866.85 m
      sailing full:   1.00 m/s
      duration:       5.80 hrs
    T=11480400.00 Condition: Site_KP18_clay.container.level<5000 and Site_KP17_clay.container.level==5000 is satisfied
    T=11480400.00 Condition: Site_KP18_clay.container.level<5000 and Site_KP17_clay.container.level==5000 is satisfied
    T=11480400.00 Condition: Site_KP17_sand.container.level<5000 and Site_KP16_sand.container.level==5000 and Site_KP17_clay.container.level==5000 is satisfied
    T=11480400.00 Clay placement to KP18_clay started
    T=11480400.00 Clay placement to KP18_clay started
    T=11480400.00 Sand placement to KP17_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 64000
      by:             Hopper contains: 1000
      to:             KP17_sand contains: 0
      distance full:  10207.64 m
      sailing full:   1.50 m/s
      duration:       1.89 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP17_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 64000
      distance empty: 10207.64 m
      sailing empty:  2.00 m/s
      duration:       1.42 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 63000
      by:             Hopper contains: 1000
      to:             KP17_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_clay contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 60000
      distance full:  10207.64 m
      sailing full:   1.50 m/s
      duration:       1.89 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP17_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 63000
      distance empty: 46410.28 m
      sailing empty:  1.60 m/s
      duration:       8.06 hrs
      distance empty: 10207.64 m
      sailing empty:  2.00 m/s
      duration:       1.42 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 62000
      by:             Hopper contains: 1000
      to:             KP17_sand contains: 2000
      distance empty: 20866.85 m
      sailing empty:  1.60 m/s
      duration:       3.62 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 59000
      by:             Transport barge 01 contains: 1000
      to:             KP18_clay contains: 0
      distance full:  10207.64 m
      sailing full:   1.50 m/s
      duration:       1.89 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP17_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 62000
      distance empty: 10207.64 m
      sailing empty:  2.00 m/s
      duration:       1.42 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 61000
      by:             Hopper contains: 1000
      to:             KP17_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 75000
      by:             Transport barge 02 contains: 1000
      to:             KP14_levvel contains: 4000
      distance full:  10207.64 m
      sailing full:   1.50 m/s
      duration:       1.89 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP17_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 61000
      distance empty: 10207.64 m
      sailing empty:  2.00 m/s
      duration:       1.42 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 60000
      by:             Hopper contains: 1000
      to:             KP17_sand contains: 4000
      distance full:  21988.56 m
      sailing full:   1.00 m/s
      duration:       6.11 hrs
      distance full:  10207.64 m
      sailing full:   1.50 m/s
      duration:       1.89 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP17_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 60000
      distance empty: 10207.64 m
      sailing empty:  2.00 m/s
      duration:       1.42 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_clay contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 59000
      distance empty: 21988.56 m
      sailing empty:  1.60 m/s
      duration:       3.82 hrs
      distance full:  47947.03 m
      sailing full:   1.00 m/s
      duration:       13.32 hrs
    T=11570400.00 Condition: Site_KP15_levvel.container.level<5000 and Site_KP14_levvel.container.level==5000 and Site_KP15_armour.container.level==5000 is satisfied
    T=11570400.00 Condition: Site_KP15_levvel.container.level<5000 and Site_KP14_levvel.container.level==5000 and Site_KP15_armour.container.level==5000 is satisfied
    T=11570400.00 Block placement to KP15_levvel started
    T=11570400.00 Block placement to KP15_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 67000
      by:             Transport barge 01 contains: 1000
      to:             KP16_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP14_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 75000
      distance empty: 47947.03 m
      sailing empty:  1.60 m/s
      duration:       8.32 hrs
      distance full:  46410.28 m
      sailing full:   1.00 m/s
      duration:       12.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 66000
      by:             Transport barge 02 contains: 1000
      to:             KP16_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 66000
      distance empty: 46410.28 m
      sailing empty:  1.60 m/s
      duration:       8.06 hrs
      distance full:  46410.28 m
      sailing full:   1.00 m/s
      duration:       12.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 58000
      by:             Transport barge 01 contains: 1000
      to:             KP18_clay contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 66000
      distance full:  21988.56 m
      sailing full:   1.00 m/s
      duration:       6.11 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 58000
      distance empty: 46410.28 m
      sailing empty:  1.60 m/s
      duration:       8.06 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 57000
      by:             Transport barge 02 contains: 1000
      to:             KP18_clay contains: 2000
      distance empty: 21988.56 m
      sailing empty:  1.60 m/s
      duration:       3.82 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 74000
      by:             Transport barge 01 contains: 1000
      to:             KP15_levvel contains: 0
      distance full:  21988.56 m
      sailing full:   1.00 m/s
      duration:       6.11 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_clay contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 57000
      distance empty: 21988.56 m
      sailing empty:  1.60 m/s
      duration:       3.82 hrs
      distance full:  47292.21 m
      sailing full:   1.00 m/s
      duration:       13.14 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 73000
      by:             Transport barge 02 contains: 1000
      to:             KP15_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 73000
      distance empty: 47292.21 m
      sailing empty:  1.60 m/s
      duration:       8.21 hrs
      distance full:  47292.21 m
      sailing full:   1.00 m/s
      duration:       13.14 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 65000
      by:             Transport barge 01 contains: 1000
      to:             KP16_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 73000
      distance empty: 47292.21 m
      sailing empty:  1.60 m/s
      duration:       8.21 hrs
      distance full:  46410.28 m
      sailing full:   1.00 m/s
      duration:       12.89 hrs
    T=11905200.00 Condition: Site_KP17_armour.container.level<5000 and Site_KP16_armour.container.level==5000 and Site_KP17_sand.container.level==5000 is satisfied
    T=11905200.00 Condition: Site_KP17_armour.container.level<5000 and Site_KP16_armour.container.level==5000 and Site_KP17_sand.container.level==5000 is satisfied
    T=11905200.00 Armour placement to KP17_armour started
    T=11905200.00 Armour placement to KP17_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 56000
      by:             Transport barge 02 contains: 1000
      to:             KP18_clay contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 65000
      distance full:  21988.56 m
      sailing full:   1.00 m/s
      duration:       6.11 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 56000
      distance empty: 46410.28 m
      sailing empty:  1.60 m/s
      duration:       8.06 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 55000
      by:             Transport barge 01 contains: 1000
      to:             KP18_clay contains: 4000
      distance empty: 21988.56 m
      sailing empty:  1.60 m/s
      duration:       3.82 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 72000
      by:             Transport barge 02 contains: 1000
      to:             KP15_levvel contains: 2000
      distance full:  21988.56 m
      sailing full:   1.00 m/s
      duration:       6.11 hrs
    T=11984400.00 Condition: Site_KP19_clay.container.level<5000 and Site_KP18_clay.container.level==5000 is satisfied
    T=11984400.00 Condition: Site_KP19_clay.container.level<5000 and Site_KP18_clay.container.level==5000 is satisfied
    T=11984400.00 Condition: Site_KP18_sand.container.level<5000 and Site_KP17_sand.container.level==5000 and Site_KP18_clay.container.level==5000 is satisfied
    T=11984400.00 Clay placement to KP19_clay started
    T=11984400.00 Clay placement to KP19_clay started
    T=11984400.00 Sand placement to KP18_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 59000
      by:             Hopper contains: 1000
      to:             KP18_sand contains: 0
      distance full:  10958.86 m
      sailing full:   1.50 m/s
      duration:       2.03 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP18_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 59000
      distance empty: 10958.86 m
      sailing empty:  2.00 m/s
      duration:       1.52 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 58000
      by:             Hopper contains: 1000
      to:             KP18_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP18_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 55000
      distance full:  10958.86 m
      sailing full:   1.50 m/s
      duration:       2.03 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP18_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 58000
      distance empty: 10958.86 m
      sailing empty:  2.00 m/s
      duration:       1.52 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 57000
      by:             Hopper contains: 1000
      to:             KP18_sand contains: 2000
      distance empty: 21988.56 m
      sailing empty:  1.60 m/s
      duration:       3.82 hrs
      distance full:  10958.86 m
      sailing full:   1.50 m/s
      duration:       2.03 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP18_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 57000
      distance full:  47292.21 m
      sailing full:   1.00 m/s
      duration:       13.14 hrs
      distance empty: 10958.86 m
      sailing empty:  2.00 m/s
      duration:       1.52 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 56000
      by:             Hopper contains: 1000
      to:             KP18_sand contains: 3000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 71000
      by:             Transport barge 01 contains: 1000
      to:             KP15_levvel contains: 3000
      distance full:  10958.86 m
      sailing full:   1.50 m/s
      duration:       2.03 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP18_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 56000
      distance empty: 10958.86 m
      sailing empty:  2.00 m/s
      duration:       1.52 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 55000
      by:             Hopper contains: 1000
      to:             KP18_sand contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 71000
      distance full:  10958.86 m
      sailing full:   1.50 m/s
      duration:       2.03 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP18_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 55000
      distance empty: 10958.86 m
      sailing empty:  2.00 m/s
      duration:       1.52 hrs
      distance empty: 47292.21 m
      sailing empty:  1.60 m/s
      duration:       8.21 hrs
      distance full:  47292.21 m
      sailing full:   1.00 m/s
      duration:       13.14 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 64000
      by:             Transport barge 02 contains: 1000
      to:             KP17_armour contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP15_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 71000
      distance empty: 47292.21 m
      sailing empty:  1.60 m/s
      duration:       8.21 hrs
      distance full:  45789.35 m
      sailing full:   1.00 m/s
      duration:       12.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 63000
      by:             Transport barge 01 contains: 1000
      to:             KP17_armour contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 63000
      distance empty: 45789.35 m
      sailing empty:  1.60 m/s
      duration:       7.95 hrs
      distance full:  45789.35 m
      sailing full:   1.00 m/s
      duration:       12.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 54000
      by:             Transport barge 02 contains: 1000
      to:             KP19_clay contains: 0
      process:        5.56 hrs
    Unloaded:
      from:           KP17_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 63000
      distance full:  23110.53 m
      sailing full:   1.00 m/s
      duration:       6.42 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_clay contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 54000
      distance empty: 45789.35 m
      sailing empty:  1.60 m/s
      duration:       7.95 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 53000
      by:             Transport barge 01 contains: 1000
      to:             KP19_clay contains: 1000
      distance empty: 23110.53 m
      sailing empty:  1.60 m/s
      duration:       4.01 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 70000
      by:             Transport barge 02 contains: 1000
      to:             KP15_levvel contains: 4000
      distance full:  23110.53 m
      sailing full:   1.00 m/s
      duration:       6.42 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_clay contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 53000
      distance empty: 23110.53 m
      sailing empty:  1.60 m/s
      duration:       4.01 hrs
      distance full:  47292.21 m
      sailing full:   1.00 m/s
      duration:       13.14 hrs
    T=12301200.00 Condition: Site_KP16_levvel.container.level<5000 and Site_KP15_levvel.container.level==5000 and Site_KP16_armour.container.level==5000 is satisfied
    T=12301200.00 Condition: Site_KP16_levvel.container.level<5000 and Site_KP15_levvel.container.level==5000 and Site_KP16_armour.container.level==5000 is satisfied
    T=12301200.00 Block placement to KP16_levvel started
    T=12301200.00 Block placement to KP16_levvel started
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 62000
      by:             Transport barge 01 contains: 1000
      to:             KP17_armour contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP15_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 70000
      distance empty: 47292.21 m
      sailing empty:  1.60 m/s
      duration:       8.21 hrs
      distance full:  45789.35 m
      sailing full:   1.00 m/s
      duration:       12.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 61000
      by:             Transport barge 02 contains: 1000
      to:             KP17_armour contains: 3000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 61000
      distance empty: 45789.35 m
      sailing empty:  1.60 m/s
      duration:       7.95 hrs
      distance full:  45789.35 m
      sailing full:   1.00 m/s
      duration:       12.72 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 52000
      by:             Transport barge 01 contains: 1000
      to:             KP19_clay contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 61000
      distance full:  23110.53 m
      sailing full:   1.00 m/s
      duration:       6.42 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_clay contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 52000
      distance empty: 45789.35 m
      sailing empty:  1.60 m/s
      duration:       7.95 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 51000
      by:             Transport barge 02 contains: 1000
      to:             KP19_clay contains: 3000
      distance empty: 23110.53 m
      sailing empty:  1.60 m/s
      duration:       4.01 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 69000
      by:             Transport barge 01 contains: 1000
      to:             KP16_levvel contains: 0
      distance full:  23110.53 m
      sailing full:   1.00 m/s
      duration:       6.42 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_clay contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 01 contains: 51000
      distance empty: 23110.53 m
      sailing empty:  1.60 m/s
      duration:       4.01 hrs
      distance full:  46655.75 m
      sailing full:   1.00 m/s
      duration:       12.96 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 68000
      by:             Transport barge 02 contains: 1000
      to:             KP16_levvel contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 68000
      distance empty: 46655.75 m
      sailing empty:  1.60 m/s
      duration:       8.10 hrs
      distance full:  46655.75 m
      sailing full:   1.00 m/s
      duration:       12.96 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 60000
      by:             Transport barge 01 contains: 1000
      to:             KP17_armour contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 68000
      distance empty: 46655.75 m
      sailing empty:  1.60 m/s
      duration:       8.10 hrs
      distance full:  45789.35 m
      sailing full:   1.00 m/s
      duration:       12.72 hrs
    T=12632400.00 Condition: Site_KP18_armour.container.level<5000 and Site_KP17_armour.container.level==5000 and Site_KP18_sand.container.level==5000 is satisfied
    T=12632400.00 Condition: Site_KP18_armour.container.level<5000 and Site_KP17_armour.container.level==5000 and Site_KP18_sand.container.level==5000 is satisfied
    T=12632400.00 Armour placement to KP18_armour started
    T=12632400.00 Armour placement to KP18_armour started
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 67000
      by:             Transport barge 02 contains: 1000
      to:             KP16_levvel contains: 2000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 60000
      distance empty: 45789.35 m
      sailing empty:  1.60 m/s
      duration:       7.95 hrs
      distance full:  46655.75 m
      sailing full:   1.00 m/s
      duration:       12.96 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 01 contains: 50000
      by:             Transport barge 01 contains: 1000
      to:             KP19_clay contains: 4000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 67000
      distance full:  23110.53 m
      sailing full:   1.00 m/s
      duration:       6.42 hrs
    T=12711600.00 Condition: Site_KP19_sand.container.level<5000 and Site_KP18_sand.container.level==5000 and Site_KP19_clay.container.level==5000 is satisfied
    T=12711600.00 Sand placement to KP19_sand started
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 54000
      by:             Hopper contains: 1000
      to:             KP19_sand contains: 0
      distance full:  11770.19 m
      sailing full:   1.50 m/s
      duration:       2.18 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP19_sand contains: 1000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 54000
      distance empty: 11770.19 m
      sailing empty:  2.00 m/s
      duration:       1.63 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 53000
      by:             Hopper contains: 1000
      to:             KP19_sand contains: 1000
      process:        5.56 hrs
    Unloaded:
      from:           KP19_clay contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 01 contains: 50000
      distance empty: 46655.75 m
      sailing empty:  1.60 m/s
      duration:       8.10 hrs
      distance full:  11770.19 m
      sailing full:   1.50 m/s
      duration:       2.18 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP19_sand contains: 2000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 53000
      distance empty: 11770.19 m
      sailing empty:  2.00 m/s
      duration:       1.63 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 52000
      by:             Hopper contains: 1000
      to:             KP19_sand contains: 2000
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 59000
      by:             Transport barge 02 contains: 1000
      to:             KP18_armour contains: 0
      distance empty: 23110.53 m
      sailing empty:  1.60 m/s
      duration:       4.01 hrs
      distance full:  11770.19 m
      sailing full:   1.50 m/s
      duration:       2.18 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP19_sand contains: 3000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 52000
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 66000
      by:             Transport barge 01 contains: 1000
      to:             KP16_levvel contains: 3000
      distance empty: 11770.19 m
      sailing empty:  2.00 m/s
      duration:       1.63 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 51000
      by:             Hopper contains: 1000
      to:             KP19_sand contains: 3000
      distance full:  11770.19 m
      sailing full:   1.50 m/s
      duration:       2.18 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP19_sand contains: 4000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 51000
      distance empty: 11770.19 m
      sailing empty:  2.00 m/s
      duration:       1.63 hrs
      process:        0.14 hrs
    Loaded:
      from:           Stock 02 contains: 50000
      by:             Hopper contains: 1000
      to:             KP19_sand contains: 4000
      distance full:  11770.19 m
      sailing full:   1.50 m/s
      duration:       2.18 hrs
      process:        0.14 hrs
    Unloaded:
      from:           KP19_sand contains: 5000
      by:             Hopper contains: 0
      to:             Stock 02 contains: 50000
      distance empty: 11770.19 m
      sailing empty:  2.00 m/s
      duration:       1.63 hrs
      distance full:  45188.25 m
      sailing full:   1.00 m/s
      duration:       12.55 hrs
      distance full:  46655.75 m
      sailing full:   1.00 m/s
      duration:       12.96 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_armour contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 59000
      process:        5.56 hrs
    Unloaded:
      from:           KP16_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 66000
      distance empty: 45188.25 m
      sailing empty:  1.60 m/s
      duration:       7.85 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 65000
      by:             Transport barge 02 contains: 1000
      to:             KP16_levvel contains: 4000
      distance empty: 46655.75 m
      sailing empty:  1.60 m/s
      duration:       8.10 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 58000
      by:             Transport barge 01 contains: 1000
      to:             KP18_armour contains: 1000
      distance full:  46655.75 m
      sailing full:   1.00 m/s
      duration:       12.96 hrs
    T=12895200.00 Condition: Site_KP17_levvel.container.level<5000 and Site_KP16_levvel.container.level==5000 and Site_KP17_armour.container.level==5000 is satisfied
    T=12895200.00 Condition: Site_KP17_levvel.container.level<5000 and Site_KP16_levvel.container.level==5000 and Site_KP17_armour.container.level==5000 is satisfied
    T=12895200.00 Block placement to KP17_levvel started
    T=12895200.00 Block placement to KP17_levvel started
      distance full:  45188.25 m
      sailing full:   1.00 m/s
      duration:       12.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP16_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 65000
      process:        5.56 hrs
    Unloaded:
      from:           KP18_armour contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 58000
      distance empty: 46655.75 m
      sailing empty:  1.60 m/s
      duration:       8.10 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 57000
      by:             Transport barge 02 contains: 1000
      to:             KP18_armour contains: 2000
      distance empty: 45188.25 m
      sailing empty:  1.60 m/s
      duration:       7.85 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 64000
      by:             Transport barge 01 contains: 1000
      to:             KP17_levvel contains: 0
      distance full:  45188.25 m
      sailing full:   1.00 m/s
      duration:       12.55 hrs
      distance full:  46038.39 m
      sailing full:   1.00 m/s
      duration:       12.79 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_armour contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 57000
      process:        5.56 hrs
    Unloaded:
      from:           KP17_levvel contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 64000
      distance empty: 45188.25 m
      sailing empty:  1.60 m/s
      duration:       7.85 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 63000
      by:             Transport barge 02 contains: 1000
      to:             KP17_levvel contains: 1000
      distance empty: 46038.39 m
      sailing empty:  1.60 m/s
      duration:       7.99 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 56000
      by:             Transport barge 01 contains: 1000
      to:             KP18_armour contains: 3000
      distance full:  46038.39 m
      sailing full:   1.00 m/s
      duration:       12.79 hrs
      distance full:  45188.25 m
      sailing full:   1.00 m/s
      duration:       12.55 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_levvel contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 63000
      process:        5.56 hrs
    Unloaded:
      from:           KP18_armour contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 56000
      distance empty: 46038.39 m
      sailing empty:  1.60 m/s
      duration:       7.99 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 55000
      by:             Transport barge 02 contains: 1000
      to:             KP18_armour contains: 4000
      distance empty: 45188.25 m
      sailing empty:  1.60 m/s
      duration:       7.85 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 62000
      by:             Transport barge 01 contains: 1000
      to:             KP17_levvel contains: 2000
      distance full:  45188.25 m
      sailing full:   1.00 m/s
      duration:       12.55 hrs
    T=13208400.00 Condition: Site_KP19_armour.container.level<5000 and Site_KP18_armour.container.level==5000 and Site_KP19_sand.container.level==5000 is satisfied
    T=13208400.00 Condition: Site_KP19_armour.container.level<5000 and Site_KP18_armour.container.level==5000 and Site_KP19_sand.container.level==5000 is satisfied
    T=13208400.00 Armour placement to KP19_armour started
    T=13208400.00 Armour placement to KP19_armour started
      process:        5.56 hrs
    Unloaded:
      from:           KP18_armour contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 55000
      distance full:  46038.39 m
      sailing full:   1.00 m/s
      duration:       12.79 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_levvel contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 62000
      distance empty: 45188.25 m
      sailing empty:  1.60 m/s
      duration:       7.85 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 61000
      by:             Transport barge 02 contains: 1000
      to:             KP17_levvel contains: 3000
      distance empty: 46038.39 m
      sailing empty:  1.60 m/s
      duration:       7.99 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 54000
      by:             Transport barge 01 contains: 1000
      to:             KP19_armour contains: 0
      distance full:  46038.39 m
      sailing full:   1.00 m/s
      duration:       12.79 hrs
      distance full:  44607.77 m
      sailing full:   1.00 m/s
      duration:       12.39 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP17_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 61000
      process:        5.56 hrs
    Unloaded:
      from:           KP19_armour contains: 1000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 54000
      distance empty: 46038.39 m
      sailing empty:  1.60 m/s
      duration:       7.99 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 53000
      by:             Transport barge 02 contains: 1000
      to:             KP19_armour contains: 1000
      distance empty: 44607.77 m
      sailing empty:  1.60 m/s
      duration:       7.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 60000
      by:             Transport barge 01 contains: 1000
      to:             KP17_levvel contains: 4000
      distance full:  44607.77 m
      sailing full:   1.00 m/s
      duration:       12.39 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_armour contains: 2000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 53000
      distance full:  46038.39 m
      sailing full:   1.00 m/s
      duration:       12.79 hrs
    T=13435200.00 Condition: Site_KP18_levvel.container.level<5000 and Site_KP17_levvel.container.level==5000 and Site_KP18_armour.container.level==5000 is satisfied
    T=13435200.00 Condition: Site_KP18_levvel.container.level<5000 and Site_KP17_levvel.container.level==5000 and Site_KP18_armour.container.level==5000 is satisfied
    T=13435200.00 Block placement to KP18_levvel started
    T=13435200.00 Block placement to KP18_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP17_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 60000
      distance empty: 44607.77 m
      sailing empty:  1.60 m/s
      duration:       7.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 59000
      by:             Transport barge 02 contains: 1000
      to:             KP18_levvel contains: 0
      distance empty: 46038.39 m
      sailing empty:  1.60 m/s
      duration:       7.99 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 52000
      by:             Transport barge 01 contains: 1000
      to:             KP19_armour contains: 2000
      distance full:  45440.90 m
      sailing full:   1.00 m/s
      duration:       12.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 59000
      distance full:  44607.77 m
      sailing full:   1.00 m/s
      duration:       12.39 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_armour contains: 3000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 52000
      distance empty: 45440.90 m
      sailing empty:  1.60 m/s
      duration:       7.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 51000
      by:             Transport barge 02 contains: 1000
      to:             KP19_armour contains: 3000
      distance empty: 44607.77 m
      sailing empty:  1.60 m/s
      duration:       7.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 58000
      by:             Transport barge 01 contains: 1000
      to:             KP18_levvel contains: 1000
      distance full:  44607.77 m
      sailing full:   1.00 m/s
      duration:       12.39 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_armour contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 03 contains: 51000
      distance full:  45440.90 m
      sailing full:   1.00 m/s
      duration:       12.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 58000
      distance empty: 44607.77 m
      sailing empty:  1.60 m/s
      duration:       7.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 57000
      by:             Transport barge 02 contains: 1000
      to:             KP18_levvel contains: 2000
      distance empty: 45440.90 m
      sailing empty:  1.60 m/s
      duration:       7.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 03 contains: 50000
      by:             Transport barge 01 contains: 1000
      to:             KP19_armour contains: 4000
      distance full:  45440.90 m
      sailing full:   1.00 m/s
      duration:       12.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 57000
      distance full:  44607.77 m
      sailing full:   1.00 m/s
      duration:       12.39 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_armour contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 03 contains: 50000
      distance empty: 45440.90 m
      sailing empty:  1.60 m/s
      duration:       7.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 56000
      by:             Transport barge 02 contains: 1000
      to:             KP18_levvel contains: 3000
      distance empty: 44607.77 m
      sailing empty:  1.60 m/s
      duration:       7.74 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 55000
      by:             Transport barge 01 contains: 1000
      to:             KP18_levvel contains: 3000
      distance full:  45440.90 m
      sailing full:   1.00 m/s
      duration:       12.62 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP18_levvel contains: 4000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 55000
      distance full:  45440.90 m
      sailing full:   1.00 m/s
      duration:       12.62 hrs
    T=13849200.00 Condition: Site_KP19_levvel.container.level<5000 and Site_KP18_levvel.container.level==5000 and Site_KP19_armour.container.level==5000 is satisfied
    T=13849200.00 Condition: Site_KP19_levvel.container.level<5000 and Site_KP18_levvel.container.level==5000 and Site_KP19_armour.container.level==5000 is satisfied
    T=13849200.00 Block placement to KP19_levvel started
    T=13849200.00 Block placement to KP19_levvel started
      process:        5.56 hrs
    Unloaded:
      from:           KP18_levvel contains: 5000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 55000
      distance empty: 45440.90 m
      sailing empty:  1.60 m/s
      duration:       7.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 54000
      by:             Transport barge 02 contains: 1000
      to:             KP19_levvel contains: 0
      distance empty: 45440.90 m
      sailing empty:  1.60 m/s
      duration:       7.89 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 53000
      by:             Transport barge 01 contains: 1000
      to:             KP19_levvel contains: 0
      distance full:  44864.07 m
      sailing full:   1.00 m/s
      duration:       12.46 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_levvel contains: 1000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 53000
      distance full:  44864.07 m
      sailing full:   1.00 m/s
      duration:       12.46 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_levvel contains: 2000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 53000
      distance empty: 44864.07 m
      sailing empty:  1.60 m/s
      duration:       7.79 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 52000
      by:             Transport barge 02 contains: 1000
      to:             KP19_levvel contains: 2000
      distance empty: 44864.07 m
      sailing empty:  1.60 m/s
      duration:       7.79 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 51000
      by:             Transport barge 01 contains: 1000
      to:             KP19_levvel contains: 2000
      distance full:  44864.07 m
      sailing full:   1.00 m/s
      duration:       12.46 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_levvel contains: 3000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 51000
      distance full:  44864.07 m
      sailing full:   1.00 m/s
      duration:       12.46 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_levvel contains: 4000
      by:             Transport barge 01 contains: 0
      to:             Stock 04 contains: 51000
      distance empty: 44864.07 m
      sailing empty:  1.60 m/s
      duration:       7.79 hrs
      process:        2.78 hrs
    Loaded:
      from:           Stock 04 contains: 50000
      by:             Transport barge 02 contains: 1000
      to:             KP19_levvel contains: 4000
      distance empty: 44864.07 m
      sailing empty:  1.60 m/s
      duration:       7.79 hrs
      distance full:  44864.07 m
      sailing full:   1.00 m/s
      duration:       12.46 hrs
      process:        5.56 hrs
    Unloaded:
      from:           KP19_levvel contains: 5000
      by:             Transport barge 02 contains: 0
      to:             Stock 04 contains: 50000
      distance empty: 44864.07 m
      sailing empty:  1.60 m/s
      duration:       7.79 hrs


Some basic visualisation on Google Earth
----------------------------------------

.. code:: ipython3

    icon = 'http://maps.google.com/mapfiles/kml/shapes/donut.png'
    size = 1
    
    kml = Kml()
    fol = kml.newfolder(name="A Folder")
    
    shared_style = Style()
    shared_style.labelstyle.color = 'ffffffff'  # White
    shared_style.labelstyle.scale = 1  
    shared_style.iconstyle.color = 'ffff0000'  # Blue
    shared_style.iconstyle.scale = 1
    shared_style.iconstyle.icon.href = icon
    
    for site in Sites:
        if not site.value or len(site.value) < 2:
            pnt = fol.newpoint(name=site.name, coords=[site.geometry["coordinates"]])
            pnt.timestamp.when = env.epoch.isoformat()
            pnt.style = shared_style
        else:
            # ignore last point because we need an endpoint
            for i, value in enumerate(site.value[:-1]):
                # convert to real dates
                begin = env.epoch + datetime.timedelta(seconds=site.t[i])
                end = env.epoch + datetime.timedelta(seconds=site.t[i+1])
                pnt = fol.newpoint(name='', coords=[site.geometry["coordinates"]])           
                # convert to string
                pnt.timespan.begin = begin.isoformat()
                pnt.timespan.end = end.isoformat()
                # use custom style if we are time dependent
                style = Style()
                style.labelstyle.color = 'ffffffff'  # White
                style.labelstyle.scale = 1  
                style.iconstyle.color = 'ffff0000'  # Blue
                style.iconstyle.scale = (value / site.container.capacity) * size
                style.iconstyle.icon.href = icon
                pnt.style = style
            begin = env.epoch + datetime.timedelta(seconds=site.t[-1])
            end = env.epoch + datetime.timedelta(seconds=env.now)
            pnt = fol.newpoint(name='', coords=[site.geometry["coordinates"]])           
            # convert to string
            pnt.timespan.begin = begin.isoformat()
            pnt.timespan.end = end.isoformat()
            # use custom style if we are time dependent
            style = Style()
            style.labelstyle.color = 'ffffffff'  # White
            style.labelstyle.scale = 1  
            style.iconstyle.color = 'ff00ff00'   # Green
            style.iconstyle.scale = (site.value[-1] / site.container.capacity) * size
            style.iconstyle.icon.href = icon
            pnt.style = style
    
    kml.save("sharedstyle.kml")

.. code:: ipython3

    # open the file
    if platform.system():
        !start ./sharedstyle.kml
    else:
        !start explorer ./sharedstyle.kml
