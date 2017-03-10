import unittest
from common.device_class_loader import DeviceClassLoader
from device.eud import Eud
from device.grid_controller import GridController
from device.grid_controller.price_logic import AveragePrice

class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        self.device_class_loader = DeviceClassLoader()

    def test_load_device(self):
        """Test loading device" from a name string"""
        device_name = "device.eud"
        TheClass = self.device_class_loader.get_device_class_from_name(device_name)
        self.assertIs(TheClass, Eud)

        device_name = "device.grid_controller"
        TheClass = self.device_class_loader.get_device_class_from_name(device_name)
        self.assertIs(TheClass, GridController)

    def test_load_by_class_name(self):
        """Test retrieving a class by passing in module and class name"""
        module_name = "device.grid_controller.price_logic"
        class_name = "AveragePrice"
        TheClass = self.device_class_loader.class_for_name(module_name, class_name)
        self.assertIs(TheClass, AveragePrice)

if __name__ == "__main__":
    unittest.main()
