## Example notebooks

The benefit of OpenCLSim is the generic set-up. This set-up allows the creation of complex logistical flows. You can run the following examples locally or as an [Azure notebook](https://notebooks.azure.com/home/projects).

* **Example 01 - Basic Hopper Operation** - Example of a trailing suction hopper dredge shipping sediment from origin to destination site.
* **Example 02 - Fuel Use** - Example of estimating fuel use on a project by keeping track of energy useage for each step of the production cycle.
* **Example 03 - Tracking Spill** - Example of a project where sediment spill limits influence project progress.
* **Example 04 - Building a Layered Dike** - Example of a construction challenge, with four separate activites, where each activity depends on the progress of the other activities.
* **Example 05 - Basic Hopper Operation on route** - Example of a trailing suction hopper dredge shipping sediment from origin to destination site while following a graph path.
* **Example 06 - Container Transfer Hub** - Example of a container transfer hub, where very large container vessels deliver containers, while smaller vessels take care of the distribution to the hinterland. Traffic follows a graph path.
* **Example 07 - Rebuild simulation from file** - Example of saving the simulation environment to a file. The code from example 01 is used, but *savesim.py* is introduced, which allows saving all parameters to a .pkl file, from which an exact copy can be simulated.
* **Example 08 - Vessel on dynamic route** - Example of a vessel using dynamic routing from the [HALEM](https://pypi.org/project/halem/) python package.
* **Example 09 - Temporary site** - Example of a project site that is used as temporary storage. It is filled and emptied after a short while, the simulation should continue until the final project rule is satisfied.