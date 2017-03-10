import unittest
from mock import MagicMock, patch, call
from device.grid_controller import GridController
from device.diesel_generator import DieselGenerator
from device.grid_controller.price_logic import AveragePriceLogic
from device.eud import Eud

class TestGridController(unittest.TestCase):
    def setUp(self):
        config = {
            "device_id": "gc_1",
        }
        # setup the grid controller device
        self.gc = GridController(config)
        # setup the callback functions
        self.gc._broadcast_new_ttie_callback = MagicMock(name="_broadcast_new_ttie_callback")
        self.gc._broadcast_new_power_callback = MagicMock(name="_broadcast_new_power_callback")
        self.gc._broadcast_new_price_callback = MagicMock(name="_broadcast_new_price_callback")
        self.gc._broadcast_new_capacity_callback = MagicMock(name="_broadcast_new_capacity_callback")

        # initialize the gc
        self.gc.init()

        # add devices
        self.gc.add_device("eud_1", Eud)
        self.gc.add_device("dg_1", DieselGenerator)
        self.gc.add_device("eud_2", Eud)
        self.gc.add_device("dg_2", DieselGenerator)

    def test_default_price_logic(self):
        """Test the price logic object is loaded"""
        # gc._price_logic should be an instance of AveragePriceLogic
        self.assertIsInstance(self.gc._price_logic, AveragePriceLogic)

    def test_adding_devices(self):
        """Test adding euds and power sources"""
        # test the count of regular devices
        self.assertEqual(self.gc.device_manager.count(), 2)
        # test the count on the power sources
        self.assertEqual(self.gc.power_source_manager.count(), 2)

    def test_set_capacity_for_power_source(self):
        """Test setting the capacity for a power source"""
        self.gc.on_capacity_change("dg_1", "gc_1", 0, 1000.0)
        self.gc.on_capacity_change("dg_2", "gc_1", 0, 5000.0)
        # make sure the capacity for the device is set correctly
        d = self.gc.power_source_manager.get("dg_1")
        self.assertEqual(d.capacity, 1000.0)
        # make sure the capacity for the device is set correctly
        d = self.gc.power_source_manager.get("dg_2")
        self.assertEqual(d.capacity, 5000.0)
        # test the sum of all the devices
        self.assertEqual(self.gc.power_source_manager.total_capacity(), 6000.0)

    def test_set_price_for_power_source(self):
        """Test setting the price for a power source"""
        # set the capacities for the two power sources
        self.gc.on_capacity_change("dg_1", "gc_1", 0, 1000.0)
        self.gc.on_capacity_change("dg_2", "gc_1", 0, 1000.0)

        # set the price for dg_1, should trigger a new price broadcast to all eud's
        self.gc.on_price_change("dg_1", "gc_1", 0, 0.2)
        calls = [
            call("gc_1", "eud_1", 0, 0.2),
            call("gc_1", "eud_2", 0, 0.2)
        ]
        self.gc._broadcast_new_price_callback.assert_has_calls(calls, any_order=False)
        # make sure the price for the device is set correctly
        d = self.gc.power_source_manager.get("dg_1")
        self.assertEqual(d.price, 0.2)

        # reset the mock object
        self.gc._broadcast_new_price_callback.reset_mock()

        # make the call to trigger the price change and callbacks
        self.gc.on_price_change("dg_2", "gc_1", 0, 0.4)

        # make sure calls were made for each of the two eud's
        mock_calls = self.gc._broadcast_new_price_callback.mock_calls
        self.assertEqual(len(mock_calls), 2)

        # now check parameters of each call
        # first call
        name, args, kwargs = mock_calls[0]
        self.assertEqual(args[0], "gc_1")
        self.assertEqual(args[1], "eud_1")
        self.assertEqual(args[2], 0)
        self.assertAlmostEqual(args[3], 0.3)
        # second call
        name, args, kwargs = mock_calls[1]
        self.assertEqual(args[0], "gc_1")
        self.assertEqual(args[1], "eud_2")
        self.assertEqual(args[2], 0)
        self.assertAlmostEqual(args[3], 0.3)

        # make sure the the price was set on the device in the grid controller
        d = self.gc.power_source_manager.get("dg_2")
        self.assertEqual(d.price, 0.4)


if __name__ == "__main__":
    unittest.main()
