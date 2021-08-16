User Guide
=================
**CERC Animation** is the graphical display to easily understand the flow of electricity in a `LPD Simulation`, along with related data such as `prices`, `message passing`, and `device status`, for both developing model algorithms and for showing the performance of the system to others.




Loading a System Configuration
--------------------

Click a `System Hyper Link` in the list to load the device configuration. Updates to the configuration will be saved.

To add a `system` to the list, choose a JSON format configuration file.

Loading a Simulation
--------------------

Once the configuration is selected, a pairing simulation file must be provided to begin the display. They can either be chosen from the dropdown menu or added. Simulations can be added with the `.log` extension.


Controls
--------

The control panel consists of a start, stop, and pause feature as well as speed adjustment controls. The slider will increase the speed of the animation up to 100x begining at real time speed. The timeline has scrubber features allowing skipping forwards and backwards with a click.

Interactivity
------------

Using JointJS, a flowchart and diagramming api, elements and links are dynamicically adjustable. The current layout can be saved in the control panel and is linked to the the system configuration.


Made by [Jude Kratzer](https://github.com/JudeKratzer/) in collaboration with Bruce Nordman, Sai Sanigepalli, and Anand Prakash
-------------------
