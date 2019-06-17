========
Examples
========

This small example guide will cover the basic start-up and the three main elements of the OpenClSim package:

- Start-Up
- Locations (Sites or stockpiles)
- Processors (Loaders, Movers or Unloaders)
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


Processors
----------

(Un)Loaders
~~~~~~~~~~~


Transporters
~~~~~~~~~~~~


Transporting Processors
~~~~~~~~~~~~~~~~~~~~~~~



Activities
----------




.. _documentation: https://simpy.readthedocs.io/en/latest/