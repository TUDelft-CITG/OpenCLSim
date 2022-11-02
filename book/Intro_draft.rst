Introduction
============

Open source Complex Logistics Simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenCLSim is a python package for rule driven scheduling of cyclic activities 
aimed at in-depth comparison of alternative operating strategies.

Book overview
~~~~~~~~~~~~~

For the design and optimization of waterborne supply chains with a cyclic
character, simulation can be a helpful tool. While simulations are not
the same as real life data, they still can save time and money as they
allow us to explore the unknown. You can investigate the performance of 
alternative execution strategies and variants of the real world (possible 
changes to the waterway and/or its infrastructure) before actual implementation.

This book provides an introduction to the use and application of the
OpenCLSim package. The goal of this book is to introduce the basics of
the package by explaining how to setup your first simulation. After the
basics this book will guide you through the set-up of more complex simulations
and show a couple of real world examples.

This book intends to serve researchers, engineers and students that
want to investigate complex logistics and its interaction with the physical system. 
OpenCLSim has grown into a community effort to collect algorithms that
can represent various cycles: sequential activities, repeating activities, parallel
activities. The modules are set up in such a manner that you can create your own
cycles depending on your needs. Via various plugins, such as a weather plugin, it is
possible to investigate the effect of changing physical conditions on cycle progress. 
Various processes can be defined as such, including mutual dependencies. A critical path
module allows to investigate what activities are critical for the overall planning. 
Due to its open-source nature, OpenCLSim facilitates an environment where connections 
with external data, models and tools can be made, such as in-house modules or databases.


Goals
~~~~~
The learning goals of this book are:
1. Learn the basics of OpenCLSim
2. Learn how to create more complex simulations with OpenCLSim
3. Learn how to apply OpenCLSim to real-world examples
4. Learn how to inspect output through logs and the registry

Context / OpenTNSim
~~~~~~~~~~~~~~~~~~~

OpenCLSim is an open-source Python package which has a sister package 
OpenTNSim. The development of the tool was started by the Ports and Waterways
department for the analysis of maritime transport. Van Oord, Deltares, Witteveen+Bos 
and Ports and Waterways joined efforts to increase the adaptability and workability 
of the tool.

OpenCLSim builds on SimPy by the addition of maritime-specific
activities: e.g. loading and unloading of items and the moving and
storing of items. Furthermore, the addition of components such as, ports,
terminals, storage, quays, cranes and vessels, allow for a real-world
maritime system to be simulated. To increase the usability of these
maritime components and activities, OpenCLSim utilises so-called *mixin
classes*. These *mixins* represent a certain set of parameters that
apply to a type of activity or component. This makes it easier to
configure complex supply chains. An example of such a mixin is the mixin
*Processor*. This class has loading and unloading functions and can be
used to represent a crane. Other mixin classes, with different
properties, can be used to represent other components in the system.
Combining different mixins can then be used to represent a port, or ac ontainer 
vessel.

It is expected that OpenCLSim and OpenTNSim will grow in the future with
the growing importance of emissions reduction and with the development
of maritime transport.
