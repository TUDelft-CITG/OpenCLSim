========
Examples
========

This small example guide will cover the basic start-up and the three main elements of the OpenClSim package:

- Start-Up (Minimal set-up)
- Locations (Sites or stockpiles)
- Resources (Processors and transporters)
- Activities (Rule-based operations)

Once the elements above are explained some small simulations examples are presented.


Start-Up
---------

Depending on the simulation it might be required to import additional libraries. The minimal set-up of an OpenCLSim project has the following import statements:

.. code:: ipython3

    # import openclsim for the logistical components
    import openclsim.model as model
    import openclsim.core as core

    # import simpy for the simulation environment
    import simpy

OpenClSim continues on the SimPy discrete event simulation package. Some components are modified, such as the resources and container objects, but the simulation environment is pure SimPy. Starting the simulation environment can be done with the following line of code. For more information in SimPy environment please refer to the SimPy `documentation`_.

.. code:: ipython3

    # Start the SimPy environment
    env = simpy.Environment()
  

Locations
---------

Basic processes do not require a location but more comprehensive simulations do. Locations are added to an OpenCLSim environment so that it becomes possible to track all events in both time and space. If a site is initiated with a container it can store materials as well. Adding a processor allows the location to load or unload as well.

Basic Location
~~~~~~~~~~~~~~

The code below illustrates how a basic location can be created using OpenClSim. Such a location can be used to add information on events in space, such as tracking movement events or creating paths to follow.

.. code:: ipython3

    # Import the library required to add coordinates
    import shapely.geometry
    
    # Create a location class
    Location = type('Location', 
                    (core.Identifiable, # Give it a name and unique UUID
                     core.HasResource,  # Add information on the number of resources
                     core.Locatable,    # Add coordinates to extract distance information
                    ),
                   {})
    
    location_data = {"env": env,                              # The SimPy environment
                     "name": "Location 01",                   # Name of the location
                     "geometry":shapely.geometry.Point(0, 0)} # The lat, lon coordinates
    
    location_01 = Location(**location_data)

Storage Location
~~~~~~~~~~~~~~~~

The code below illustrates how a location can be created that is capable of storing an amount. Such a location can be used by the OpenClSim.model activities as origin or destination. 

.. code:: ipython3

    # Import the library required to add coordinates
    import shapely.geometry
    
    # Create a location class
    StorageLocation = type('StorageLocation', 
                    (core.Identifiable, # Give it a name and unique UUID
                     core.HasResource,  # Add information on the number of resources
                     core.Locatable,    # Add coordinates to extract distance information
                     core.HasContainer, # Add information on storage capacity
                    ),
                   {})
    
    location_data = {"env": env,                              # The SimPy environment
                     "name": "Location 02",                   # Name of the location
                     "geometry":shapely.geometry.Point(0, 0), # The lat, lon coordinates
                     "capacity": 10_000}                      # The maximum number of units
    
    location_02 = StorageLocation(**location_data)

Processing Storage Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The code below illustrates how a location can be created that is capable of storing an amount. Additional to the storage location, a processing- and storage location can be used as both the origin and loader or destination and unloader in a OpenClSim.model activity. 

.. code:: ipython3

    # Import the library required to add coordinates
    import shapely.geometry
    
    # Create a location class
    ProcessingStorageLocation = type('ProcessingStorageLocation', 
                    (core.Identifiable, # Give it a name and unique UUID
                     core.HasResource,  # Add information on the number of resources
                     core.Locatable,    # Add coordinates to extract distance information
                     core.HasContainer, # Add information on storage capacity
                     core.Processor,    # Add information on processing
                    ),
                   {})
    
    # Create a processing function
    processing_rate = lambda x: x

    location_data = {"env": env,                              # The SimPy environment
                     "name": "Location 03",                   # Name of the location
                     "geometry":shapely.geometry.Point(0, 0), # The lat, lon coordinates
                     "capacity": 10_000,                      # The maximum number of units
                     "loading_func": processing_rate,         # Loading rate of 1 unit per 1 unit time
                     "unloading_func": processing_rate}       # Unloading rate of 1 unit per 1 unit time
    
    location_03 = ProcessingStorageLocation(**location_data)


Optionally a *OpenCLSim.core.log* mixin can be added to all locations to keep track of all the events that are taking place.


Resources
----------

OpenCLSim resources can be used to process and transport units. The OpenCLSim.model activity class requires a loader, an unloader and a mover, this are examples of resources. A resource will always interact with another resource in an OpenClSim.model activity, but it is possible to initiate a simpy process to keep track of a single resource.

Processing Resource
~~~~~~~~~~~~~~~~~~~

An example of a processing resource is a harbour crane, it processes units from a storage location to a transporting resource or vice versa. In the OpenClSim.model activity such a processing resource could be selected as the loader or unloader. The example code is presented below.

.. code:: ipython3

    # Create a resource
    ProcessingResource = type('ProcessingResource', 
                    (core.Identifiable, # Give it a name and unique UUID
                     core.HasResource,  # Add information on the number of resources
                     core.Locatable,    # Add coordinates to extract distance information
                     core.Processor,    # Add information on processing
                    ),
                   {})
    
    # The next step is to define all the required parameters for the defined metaclass
    # Create a processing function
    processing_rate = lambda x: x

    location_resource = {"env": env,                              # The SimPy environment
                         "name": "Resource 01",                   # Name of the location
                         "geometry":location_01.geometry, # The lat, lon coordinates
                     "loading_func": processing_rate,         # Loading rate of 1 unit per 1 unit time
                     "unloading_func": processing_rate}       # Unloading rate of 1 unit per 1 unit time
    
    # Create an object based on the metaclass and vessel data
    resource_01 = ProcessingStorageLocation(**location_data)


Transporting Resource
~~~~~~~~~~~~~~~~~~~~~

A harbour crane will service transporting resources. To continue with the harbour crane example, basically any vessel is a transporting resource because it is capable of moving units from location A to location B. In the OpenClSim.model activity such a processing resource could be selected as the mover.

.. code:: ipython3

    # Create a resource
    TransportingResource = type('TransportingResource', 
                        (core.Identifiable, # Give it a name and unique UUID
                         core.HasResource,  # Add information on the number of resources
                         core.Locatable,    # Add coordinates to extract distance information
                         core.Movable,      # It can move
                         core.HasContainer, # It can transport an amount
                         core.HasResource,  # Add information on serving equipment
                         ),
                        {})
    
    # The next step is to define all the required parameters for the defined metaclass
    # For more realistic simulation you might want to have speed dependent on the filling degree
    v_full  = 8     # meters per second
    v_empty = 5     # meters per second

    def variable_speed(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty
    
    # Other variables
    data_vessel = {
               "env": simpy.Environment(),                   # The simpy environment 
               "name": "Resource 02",                   # Name of the location
               "geometry":location_01.geometry, # The lat, lon coordinates
               "capacity": 5_000,                            # Capacity of the vessel 
               "compute_v": variable_speed(v_empty, v_full), # Variable speed 
               }
    
    # Create an object based on the metaclass and vessel data
    vessel_02 = ContainerVessel(**data_vessel)

Transporting Processing Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, some resources are capable of both processing and moving units. Examples are dredging vessels or container vessels with deck cranes. These specific vessels have the unique property that they can act as the loader, unloader and mover in the OpenClSim.model activity.

.. code:: ipython3

    # Create a resource
    TransportingResource = type('TransportingResource', 
                        (core.Identifiable, # Give it a name and unique UUID
                         core.HasResource,  # Add information on the number of resources
                         core.Locatable,    # Add coordinates to extract distance information
                         core.Movable,      # It can move
                         core.HasContainer, # It can transport an amount
                         core.HasResource,  # Add information on serving equipment
                         core.Processor,    # Add information on processing
                         ),
                        {})
    
    # The next step is to define all the required parameters for the defined metaclass
    # For more realistic simulation you might want to have speed dependent on the filling degree
    v_full  = 8     # meters per second
    v_empty = 5     # meters per second

    def variable_speed(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty
    
    # Create a processing function
    processing_rate = lambda x: x
    
    # Other variables
    data_vessel = {
               "env": simpy.Environment(),                   # The simpy environment 
               "name": "Resource 02",                   # Name of the location
               "geometry":location_01.geometry, # The lat, lon coordinates
               "capacity": 5_000,                            # Capacity of the vessel 
               "compute_v": variable_speed(v_empty, v_full), # Variable speed 
                     "loading_func": processing_rate,         # Loading rate of 1 unit per 1 unit time
                     "unloading_func": processing_rate,       # Unloading rate of 1 unit per 1 unit time
               }
    
    # Create an object based on the metaclass and vessel data
    vessel_03 = ContainerVessel(**data_vessel)


Activities
----------

Unconditional
~~~~~~~~~~~~~


Start Events
~~~~~~~~~~~~


Stop Events
~~~~~~~~~~~


Simulations
-----------

SimPy processes
~~~~~~~~~~~~~~~

OpenClSim model
~~~~~~~~~~~~~~~

.. _documentation: https://simpy.readthedocs.io/en/latest/