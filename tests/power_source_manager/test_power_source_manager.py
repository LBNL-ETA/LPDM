import unittest
from device.grid_controller.power_source_manager import PowerSourceManager
from device.grid_controller.power_source_manager import PowerSourceItem
from device.power_source import PowerSource
from device.diesel_generator import DieselGenerator
from device.eud import Eud

class TestPowerSourceManager(unittest.TestCase):
    def setUp(self):
        self.power_source_manager = PowerSourceManager()

    def test_add_power_source(self):
        """Test addition of power sources"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.assertEqual(self.power_source_manager.count(), 1)

    def test_add_non_power_source(self):
        """Test adding a non-PowerSource, should raise an Exception"""
        with self.assertRaises(Exception):
            self.power_source_manager.add("eud_1", Eud)

    def test_add_duplicate_device_id(self):
        """Test adding duplicate device_id's"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        with self.assertRaises(Exception):
            self.power_source_manager.add("dg_1", DieselGenerator)

    def test_get_device_by_id(self):
        """Test getting a device by its ID"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)

        device = self.power_source_manager.get("dg_2")
        self.assertEqual(device.device_id, "dg_2")

    def test_set_device_capacity(self):
        """Test setting the capacity for a device_id"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)

        # set the capacity for dg_2
        self.power_source_manager.set_capacity("dg_2", 120.0)
        device = self.power_source_manager.get("dg_2")
        self.assertEqual(device.capacity, 120.0)

    def test_set_device_price(self):
        """Test setting the price for a device_id"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)

        # set the price for dg_2
        self.power_source_manager.set_price("dg_2", 0.15)
        device = self.power_source_manager.get("dg_2")
        self.assertEqual(device.price, 0.15)

    def test_set_device_load(self):
        """Test setting the load for a device_id"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)

        # set the capacity for the device
        self.power_source_manager.set_capacity("dg_2", 120.0)
        # set the load for dg_2, has to be < than capacity
        self.power_source_manager.set_load("dg_2", 0.15)
        device = self.power_source_manager.get("dg_2")
        self.assertEqual(device.load, 0.15)

    def test_set_device_load_greater_than_capacity(self):
        """Test setting the load for a device_id that is > than the capacity"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)

        # set the capacity for the device
        self.power_source_manager.set_capacity("dg_2", 120.0)
        # set the load for dg_2, has to be < than capacity
        with self.assertRaises(Exception):
            self.power_source_manager.set_load("dg_2", 125.0)

    def test_getting_available_power_sources(self):
        """Test retrieving power sources that have non-zero capacities"""
        self.power_source_manager.add("dg_1", DieselGenerator)
        self.power_source_manager.add("dg_2", DieselGenerator)
        self.power_source_manager.add("dg_3", DieselGenerator)

        # set the capacity for the device
        self.power_source_manager.set_capacity("dg_1", 0.0)
        self.power_source_manager.set_capacity("dg_2", 120.0)
        # don't set the capacity for dg_3, should be None

        available = self.power_source_manager.get_available_power_sources()
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].device_id, "dg_2")


if __name__ == "__main__":
    unittest.main()
