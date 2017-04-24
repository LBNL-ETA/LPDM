import importlib
import logging

class DeviceClassLoader(object):
    """
    Get a LPDM device class from a string.
    This is assuming a module structure for the device classes as 'device.name',
    where all the specific implementations of a device, such as an air conditioner, are
    stored as subfolders under a main 'device' folder, e.g. device.air_conditioner.
    """

    def __init__(self):
        self.logger = logging.getLogger("lpdm")

    def get_device_class_from_name(self, module_name):
        """Get a device class from the folder name"""
        # build the class name
        # which should be the camelcase version of the device_name, which is snakecase
        # eg diesel_generator = DieselGenerator
        parts = module_name.split(".")
        class_name = "".join([p.capitalize() for p in parts[-1].split("_")])
        return self.class_for_name(module_name, class_name)

    def class_for_name(self, module_name, class_name):
        # load the module, will raise ImportError if module cannot be loaded
        m = importlib.import_module(module_name)
        # get the class, will raise AttributeError if class cannot be found
        c = getattr(m, class_name)
        return c
