Creating Your Own Devices
=========================

How the Simulation Loads Devices
--------------------------------
The **device_type** key in the device json configuration file tells the simulation which device object to load.

The devices are defined as part of a Python package, so each folder within **device/** must have a file named **__init__.py**.

The **device/** folder contains subfolders for each device.  Each subfolder is named as the
snake case version of the device class name, e.g. the AirConditioner device class is stored in a
folder named air_contitioner.

The name of the file that contains the device class definition can be named anything.  The **__init__.py** file is responsible for importing
the class into the namespace, e.g. ``from the_py_file_containing_class import AirConditioner``.

When the simulation is parsing the json file, it reads the **device_type** for each device and attempts to load
the class object as part of the device package, e.g. ``from device.air_conditioner import AirConditioner``.

Steps for Creating Devices
--------------------------

1. Create a folder in **device/** with a name that is the 'snake case' version of your device name.
   So if you wanted to create a device class named **HeatPump**, you would create a folder named **heat_pump**.

2. Create the new device class in a file inside the new folder. The new device must be a subclass of the **Device** base class,
   or another existing device.

3. Inside the new device folder, create a file named **__init__.py**.  Inside that file import the new device class.

4. To use your new device, set the **device_type** to the 'snake case' name of your device class inside the configuration file.

