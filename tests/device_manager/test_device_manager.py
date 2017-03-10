import unittest
from device.grid_controller.device_manager import DeviceManager
from device.grid_controller.device_manager import DeviceItem
from device.eud import Eud

class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        self.device_manager = DeviceManager()

    def test_add_device(self):
        """Test adding a device"""
        self.device_manager.add("eud_1", Eud)
        self.device_manager.add("eud_2", Eud)
        self.assertEqual(self.device_manager.count(), 2)

    def test_add_duplicate_device_id(self):
        """Test adding duplicate device_id's"""
        self.device_manager.add("eud_1", Eud)
        with self.assertRaises(Exception):
            self.device_manager.add("eud_1", Eud)

    def test_get_device_by_id(self):
        """Test getting a device by its ID"""
        self.device_manager.add("eud_1", Eud)
        self.device_manager.add("eud_2", Eud)

        device = self.device_manager.get("eud_2")
        self.assertEqual(device.device_id, "eud_2")

    def test_set_device_load(self):
        """Test setting the load for a device_id"""
        self.device_manager.add("eud_1", Eud)
        self.device_manager.add("eud_2", Eud)

        # set the load for eud_2, has to be < than capacity
        self.device_manager.set_load("eud_2", 0.15)
        device = self.device_manager.get("eud_2")
        self.assertEqual(device.load, 0.15)

if __name__ == "__main__":
    unittest.main()
