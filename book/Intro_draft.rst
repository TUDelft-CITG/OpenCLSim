Introduction
============

Open source Complex Logistics Simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenCLSim is a python package for the rule driven scheduling of cyclic activities 
for in-depth comparison of alternative operating strategies.

Book overview
~~~~~~~~~~~~~

For the design and optimization of waterborne supply chains with a cyclic
charater, simulation can be a helpful tool. While simulations are not
the same as real life data, they still can save time and money as they
allow us to explore the unknown. You can simulate alternative execution strategies
and variants of the real world (possible changes to the waterway and/or its 
infrastructure).

This book provides an introduction to the use and application of the
OpenCLSim package. The goal of this book is to introduce the basics of
the package by explaining how to setup your first simulation. The
book will guide you through the use of real-life data and the
simulation of more complex systems by explaining the use of shape
files, multiple vessel generators and the visualization of sailed
paths. Finally, it addresses how to estimate energy consumption, fuel use and
emissions from the simulations.

This book intends to serve researchers, engineers and students that
want to simulate vessel traffic on marine and inland waterways. OpenTNSim
has grown into a community effort to collect algorithms that
can represent sailing strategies, engines choices/setting, and structures
(e.g. locks). Using discrete event simulations (schematized using an
event log, using queuing and asynchronous tasks), the model is well
suited to be integrated into the logistical chain of ports and
waterways. Due to its open-source nature, OpenTNSim facilitates an
environment where connections with external data, models and tools can
be made, such as digital twins.


Goals
~~~~~
The learning goals of this book are:
1. Learn the basics of OpenCLSim
2. Learn how to apply real-life data in OpenCLSim
3. Learn how to make more advanced simulations
4. Learn how to retrieve emissions and energy usage data

Context / OpenTNSim
~~~~~~~~~~~~~~~~~~~

OpenCLSim is an open-source Python package which has a sister package 
OpenCLSim. OpenCLSim was developed by the Ports and
Waterways (P&W) department of TU Delft, Van Oord and Deltares. The
development of the tool was started by the P&W department for the
analysis of maritime transport. Van Oord, Deltares and P&W joined
efforts to increase the adaptability and workability of the tool.

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
Combining different mixins can then be used to represent a port, or acontainer vessel [ref OpenCLSim article].

It is expected that OpenCLSim and OpenTNSim will grow in the future with
the growing importance of emissions reduction and with the development
of maritime transport.
