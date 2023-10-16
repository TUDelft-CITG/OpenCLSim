=====
Usage
=====


Import required components
--------------------------

To use OpenCLSim in a project you have to import the following three components:

.. code:: python3
    # Import simpy for the simulation environment
    import simpy
    # Shapely for geometries
    import shapely

    # Import openclsim for the logistical components
    import openclsim.model as model
    import openclsim.core as core



Using Mixins and Metaclasses
-----------------------------

The Open Complex Logistics Simulation package is developed with the goal of reusable and generic components in mind. A new class can be instatiated by combining mixins from the *openclsim.core*, such as presented below. The following lines of code demonstrate how a containervessel can be defined:

.. code:: python3
    # Define the core components
    # A generic class for an object that can move and transport material
    ContainerVessel = type(
        'ContainerVessel',
        (
            core.ContainerDependentMovable,# It can transport an amount
            core.HasResource,              # Add information on serving equipment
            core.Identifiable,             # Give it a name and unique UUID
            core.Log,                      # Allow logging of all discrete events
        ),
        {}
    )

    # The next step is to define all the required parameters for the defined metaclass
    # For more realistic simulation you might want to have speed dependent on the filling degree
    v_full  = 8     # meters per second
    v_empty = 5     # meters per second

    def variable_speed(v_empty, v_full):
        return lambda x: x * (v_full - v_empty) + v_empty

    # Other variables
    data_vessel = {
        "env": simpy.Environment(),                   # The simpy environment
        "name": "Vessel 01",                          # Name
        "geometry": shapely.geometry.Point(0, 0),     # The lat, lon coordinates
        "capacity": 5_000,                            # Capacity of the vessel
        "compute_v": variable_speed(v_empty, v_full), # Variable speed
    }

    # Create an object based on the metaclass and vessel data
    vessel_01 = ContainerVessel(**data_vessel)

For more elaboration and examples please check the `examples`_ documentation. In-depth `Jupyter Notebooks`_ can also be used.

.. _examples: https://openclsim.readthedocs.io/en/latest/examples
.. _Jupyter Notebooks: https://github.com/TUDelft-CITG/OpenCLSim-Notebooks
