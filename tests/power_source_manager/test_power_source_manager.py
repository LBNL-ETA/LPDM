import unittest
from device.simulated.grid_controller.power_source_manager import PowerSourceManager
from device.simulated.grid_controller.power_source_manager import PowerSourceItem
from device.simulated.power_source import PowerSource
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.eud import Eud

class TestPowerSourceManager(unittest.TestCase):
    def setUp(self):
        self.psm = PowerSourceManager()

    def test_has_available_power_sources(self):
        """Test if has available power sources"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        self.psm.add("dg_3", DieselGenerator)
        dg1 = self.psm.get("dg_1")
        dg2 = self.psm.get("dg_2")
        dg3 = self.psm.get("dg_3")

        self.assertFalse(self.psm.has_available_power_sources())
        self.psm.set_price("dg_1", 0.15)
        self.psm.set_capacity("dg_1", 1000.0)
        self.assertTrue(self.psm.has_available_power_sources())

    def test_add_power_source(self):
        """Test addition of power sources"""
        self.psm.add("dg_1", DieselGenerator)
        self.assertEqual(self.psm.count(), 1)

    def test_add_non_power_source(self):
        """Test adding a non-PowerSource, should raise an Exception"""
        with self.assertRaises(Exception):
            self.psm.add("eud_1", Eud)

    def test_add_duplicate_device_id(self):
        """Test adding duplicate device_id's"""
        self.psm.add("dg_1", DieselGenerator)
        with self.assertRaises(Exception):
            self.psm.add("dg_1", DieselGenerator)

    def test_get_device_by_id(self):
        """Test getting a device by its ID"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        device = self.psm.get("dg_2")
        self.assertEqual(device.device_id, "dg_2")

    def test_get_all_devices(self):
        """Test getting all the powersources"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        items = self.psm.get()
        self.assertEqual(len(items), 2)

    def test_set_device_capacity(self):
        """Test setting the capacity for a device_id"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        # set the capacity for dg_2
        self.psm.set_capacity("dg_2", 120.0)
        device = self.psm.get("dg_2")
        self.assertEqual(device.capacity, 120.0)
        self.assertTrue(device.capacity_changed)

        self.psm.set_price("dg_2", 0.3)

    def test_set_device_price(self):
        """Test setting the price for a device_id"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        # set the price for dg_2
        self.psm.set_price("dg_2", 0.15)
        device = self.psm.get("dg_2")
        self.assertEqual(device.price, 0.15)

    def test_set_device_load(self):
        """Test setting the load for a device_id"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        # set the capacity for the device
        self.psm.set_capacity("dg_2", 120.0)

        # price has not been set so should raise an Exception
        with self.assertRaises(Exception):
            self.psm.set_load("dg_2", 15)

        self.psm.set_price("dg_2", 0.30)
        # set the load for dg_2, has to be < than capacity
        self.psm.set_load("dg_2", 0.15)
        device = self.psm.get("dg_2")
        self.assertEqual(device.load, 0.15)
        self.assertTrue(device.load_changed)

    def test_set_device_load_greater_than_capacity(self):
        """Test setting the load for a device_id that is > than the capacity"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        # set the capacity for the device
        self.psm.set_capacity("dg_2", 120.0)
        # set the load for dg_2, has to be < than capacity
        with self.assertRaises(Exception):
            self.psm.set_load("dg_2", 125.0)

    def test_getting_available_power_sources(self):
        """Test retrieving power sources that have non-zero capacities"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        self.psm.add("dg_3", DieselGenerator)

        # set the capacity for the device
        self.psm.set_capacity("dg_1", 0.0)
        self.psm.set_price("dg_1", 0.15)
        self.psm.set_capacity("dg_2", 120.0)
        self.psm.set_price("dg_2", 0.30)
        # don't set the capacity for dg_3, should be None

        available = self.psm.get_available_power_sources()
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].device_id, "dg_2")

    def test_total_capacity(self):
        """Test summing up the capacity for all available power sources"""
        # add the devices
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        self.assertEqual(self.psm.total_capacity(), 0.0)

        # set the capacity and pric3
        self.psm.set_capacity("dg_1", 0.0)
        self.psm.set_capacity("dg_2", 120.0)
        # this should be zero because a price has not been set
        self.assertEqual(self.psm.total_capacity(), 0.0)

        # set the prices
        self.psm.set_price("dg_1", 0.0)
        self.psm.set_price("dg_2", 0.30)
        # should be 120
        self.assertEqual(self.psm.total_capacity(), 120.0)

        self.psm.set_capacity("dg_1", 200.0)
        self.assertEqual(self.psm.total_capacity(), 320.0)

    def test_total_load(self):
        """Test summing up the load for all available power sources"""
        # add the devices
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        self.assertEqual(self.psm.total_load(), 0.0)

        # set the capacity
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)
        # set the prices
        self.psm.set_price("dg_1", 0.0)
        self.psm.set_price("dg_2", 0.30)

        self.psm.set_load("dg_1", 200.0)
        self.assertEqual(self.psm.total_load(), 200.0)

    def test_can_handle_load(self):
        """Test that the psm can check if there is enough capacity available"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)

        # no capacities or prices set so should not be able to handle load
        self.assertFalse(self.psm.can_handle_load(100.0))

        # set the capacity
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)

        # no prices set so should not be able to handle load
        self.assertFalse(self.psm.can_handle_load(100.0))
        # set the prices
        self.psm.set_price("dg_1", 0.0)
        self.psm.set_price("dg_2", 0.30)

        self.assertTrue(self.psm.can_handle_load(100.0))
        self.assertTrue(self.psm.can_handle_load(1001.0))
        self.assertTrue(self.psm.can_handle_load(2000.0))
        self.assertFalse(self.psm.can_handle_load(2001.0))

    def test_add_load(self):
        """Test adding load among various power sources"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        self.psm.add("dg_3", DieselGenerator)

        # no capacities or prices set so should not be able to handle load
        self.assertFalse(self.psm.add_load(100.0))

        # set the capacity
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)
        self.psm.set_capacity("dg_3", 1000.0)

        # no prices set so should not be able to handle load
        self.assertFalse(self.psm.add_load(100.0))

        # set the prices
        self.psm.set_price("dg_1", 0.15)
        self.psm.set_price("dg_2", 0.30)

        # now should be able to handle 2000 W
        self.assertFalse(self.psm.can_handle_load(2001.0))
        self.assertFalse(self.psm.add_load(2001.0))

        # set dg3 to 0.0 (lowest price)
        self.psm.set_price("dg_3", 0.0)
        # now should be able to handle 3 kW
        # adding load in order of lowest to highest price
        # adding 900 W should put it on dg_3
        self.assertTrue(self.psm.add_load(900.0))
        d = self.psm.get("dg_3")
        self.assertEqual(d.load, 900.0)

        # adding 200.0 W should fill out remaining available for dg_3 and put rest on dg_1
        self.assertTrue(self.psm.add_load(200.0))
        d = self.psm.get("dg_3")
        self.assertEqual(d.load, 1000.0)
        d = self.psm.get("dg_1")
        self.assertEqual(d.load, 100.0)

        # adding 1000 W should fill out the rest of dg_1 and put 100 W on dg_2
        self.assertTrue(self.psm.add_load(1000.0))
        d = self.psm.get("dg_3")
        self.assertEqual(d.load, 1000.0)
        d = self.psm.get("dg_1")
        self.assertEqual(d.load, 1000.0)
        d = self.psm.get("dg_2")
        self.assertEqual(d.load, 100.0)

    def test_changed_flags(self):
        """Test the boolean change flags for capacity and load"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        dg1 = self.psm.get("dg_1")
        dg2 = self.psm.get("dg_2")

        self.psm.set_capacity("dg_1", 100.0)
        self.psm.set_price("dg_1", 0.15)
        self.psm.set_load("dg_1", 2.0)
        self.assertTrue(dg1.capacity_changed)
        self.assertTrue(dg1.load_changed)
        self.assertFalse(dg2.capacity_changed)
        self.assertFalse(dg2.load_changed)

        self.psm.reset_changed()

        self.psm.set_capacity("dg_2", 2000.0)
        self.assertTrue(dg2.capacity_changed)
        self.assertFalse(dg2.load_changed)
        self.assertFalse(dg1.capacity_changed)
        self.assertFalse(dg1.load_changed)

    def test_optimize_load(self):
        """Test optimizing load"""
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        self.psm.add("dg_3", DieselGenerator)
        dg1 = self.psm.get("dg_1")
        dg2 = self.psm.get("dg_2")
        dg3 = self.psm.get("dg_3")

        # set the capacity
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)
        self.psm.set_capacity("dg_3", 1000.0)

        # set the price
        self.psm.set_price("dg_1", 0.15)
        self.psm.set_price("dg_2", 0.0)
        self.psm.set_price("dg_3", 0.30)

        # adding load should go to cheapeast priced power source avaialable (dg_2)
        self.psm.add_load(1000.0)
        self.assertEqual(dg2.load, 1000)

        # changing the price and optimizing the load should move the load to the cheapeast priced power source
        dg2.price = 0.45
        self.psm.optimize_load()
        self.assertEqual(dg1.load, 1000)
        self.assertEqual(dg2.load, 0)
        self.assertEqual(self.psm.total_load(), 1000)

        # dg1 = 0.15, dg2 = 0.45, dg3 = 0.30
        # add another 500W, should now go to the 2nd cheapeast power source (dg_3)
        self.psm.add_load(500.0)
        self.assertEqual(dg1.load, 1000)
        self.assertEqual(dg2.load, 0)
        self.assertEqual(dg3.load, 500)

        # set new prices
        self.psm.set_price("dg_2", 0.0)
        # now prices are dg1 = 0.15, dg2 = 0.0, dg3 = 0.30
        self.psm.optimize_load()
        self.assertEqual(dg1.load, 500)
        self.assertEqual(dg2.load, 1000)
        self.assertEqual(dg3.load, 0)


if __name__ == "__main__":
    unittest.main()
