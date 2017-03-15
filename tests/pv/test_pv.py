import unittest
from mock import MagicMock, patch
from device.pv import Pv

class TestPv(unittest.TestCase):
    def setUp(self):
        config = {
            "device_id": "pv_1"
        }

        self.device = Pv(config)

        self.device._grid_controller_id = "gc_1"
        self.device._broadcast_new_ttie_callback = MagicMock(name="_broadcast_new_ttie_callback")
        self.device._broadcast_new_power_callback = MagicMock(name="_broadcast_new_power_callback")
        self.device._broadcast_new_price_callback = MagicMock(name="_broadcast_new_price_callback")
        self.device._broadcast_new_capacity_callback = MagicMock(name="_broadcast_new_capacity_callback")

    def test_for_initial_price(self):
        """Make sure there is a price for electricity at t == 0"""
        self.device.init()
        self.assertIsNot(self.device._price, None)

    def test_for_initial_price_broadcast(self):
        """Make sure that the electricity price is sent to the grid controller at t = 0"""
        self.device.init()
        self.device._broadcast_new_price_callback.assert_called_with(
            self.device._device_id, # source device_id
            self.device._grid_controller_id, # target device id
            0, # current time
            self.device._price # fuel price
        )

    def test_for_initial_capacity(self):
        """Make sure the device has a capacity value at t = 0"""
        self.device.init()
        self.assertIsNot(self.device._current_capacity, None)

    def test_for_initial_capacity_broadcast(self):
        """Make sure that the capacity is sent to the grid controller at t = 0"""
        self.device.init()
        self.device._broadcast_new_capacity_callback.assert_called_with(
            self.device._device_id, # source device_id
            self.device._grid_controller_id, # target device id
            0, # current time
            self.device._current_capacity # capacity of the device
        )

    # def test_make_unavailable(self):
        # """Test making the power source unavailable, ie _current_capacity = 0"""
        # self.device.init()
        # self.device.make_unavailable()
        # self.assertEqual(self.device._current_capacity, 0.0)

    # def test_make_available(self):
        # """Test making the power source available, ie _current_capacity > 0"""
        # self.device.init()
        # self.device.make_unavailable()
        # self.device.make_available()
        # self.assertGreater(self.device._current_capacity, 0.0)

    # def test_set_power_level_unavailable(self):
        # """Test setting the power level when it is unavailable (ie capacity == 0)"""
        # self.device.init()
        # self.device.make_unavailable()
        # with self.assertRaises(Exception):
            # self.device.on_power_change("gc_1", self.device.device_id, 0, 100.0)

if __name__ == "__main__":
    unittest.main()

