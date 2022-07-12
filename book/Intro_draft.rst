Introduction
============

Open source Transport Network Simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenTNSim is a python package for the investigation of traffic behaviour
on networks. It can be used to investigate how water transport chains
interact with the waterway network and its infrastructure. Simulations
can be used  to compare the consequences of traffic scenarios and network
configurations.

Book overview
~~~~~~~~~~~~~

For the design and optimization of port water areas and inland
waterways, simulation can be a helpful tool. While simulations are not
the same as real life data, they still can save time and money as they
allow us to explore the unknown. You can simulate unseen
events (incidents, low/high water extremes) and variants of the real world
(possible changes to the waterway and/or its infrastructure).

OpenTNSim simulates vessels navigating (existing or planned) waterway networks.
Useful features are visualisation of sailed paths (route selection, traffic
intensities, transport capacity), analysis of the behaviour and interaction
of (random) generated vessels, integration of real-world data (water levels,
currents) and estimation of energy consumption, fuel use and emissions of vessels.
With the increasing demand for sea-going and inland shipping and societal changes
related to digitalisation, sustainability, and climate change, OpenTNSim can help
researchers and practitioners to investigate the complexity of water transport
networks and support decision making under conditions of uncertainty.

This book provides an introduction to the use and application of the
OpenTNSim package. The goal of this book is to introduce the basics of
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
1. Learn the basics of OpenTNSim
2. Learn how to apply real-life data in OpenTNSim
3. Learn how to make more advanced simulations
4. Learn how to retrieve emissions and energy usage data

Context / OpenCLSim
~~~~~~~~~~~~~~~~~~~

OpenTNSim is an open-source Python package which is an adaptation of
the OpenCLSim package. OpenCLSim was developed by the Ports and
Waterways (P&W) department of TU Delft, Van Oord and Deltares. The
development of the tool was started by the P&W department for the
analysis of maritime transport. Van Oord, Deltares and P&W joined
efforts to increase the adaptability and workability of the tool.

Simulation of real-world processes requires a representation of the
real-world system and a way to represent the different processes in such
a system. More importantly, the simulation of real-world processes
requires a way to incorporate congestion and delay as these are
unavoidable in in real life. OpenCLSim (and OpenTNSim) utilises the
SimPy package for this kind of event simulation. SimPy revolves around
the passing fixed periods of time that represent different processes
[ref Team Simpy]. The outcome of a such a process can be either a
triggered event or a non-triggered event. When an event is triggered and
completed, the process can be a success or a failure. The failure can be
inherent (caused by the process itself) or caused by the interruption of
a different process [ref OpenCLSim article]. In SimPy it is possible to
create interdependencies between different processes and thus create a
schematisation of a real-world chain of events.

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
Combining different mixins can then be used to represent a port, or a
container vessel [ref OpenCLSim article].

It is expected that OpenCLSim and OpenTNSim will grow in the future with
the growing importance of emissions reduction and with the development
of maritime transport.
