import unittest
from mock import MagicMock, patch
from device.diesel_generator import DieselGenerator

class TestDieselGenerator(unittest.TestCase):
    def setUp(self):
        config = {
            "device_id": "device_1",
            "fuel_tank_capacity": 100.0, # set to 100 gallons
            "fuel_level": 100.0, # set to 100% full
            "days_to_refuel": 7, # 7 days to refuel
            "capacity": 2000.0 # 2000 W capacity
        }

        self.device = DieselGenerator(config)

        self.device._grid_controller_id = "gc_1"
        self.device._broadcast_new_ttie_callback = MagicMock(name="_broadcast_new_ttie_callback")
        self.device._broadcast_new_power_callback = MagicMock(name="_broadcast_new_power_callback")
        self.device._broadcast_new_price_callback = MagicMock(name="_broadcast_new_price_callback")
        self.device._broadcast_new_capacity_callback = MagicMock(name="_broadcast_new_capacity_callback")

    def test_for_initial_price(self):
        """Make sure there is a price for electricity at t == 0"""
        self.device.init()
        self.assertGreater(self.device._current_fuel_price, 0)

    def test_for_initial_price_broadcast(self):
        """Make sure that the electricity price is sent to the grid controller at t = 0"""
        self.device.init()
        self.device._broadcast_new_price_callback.assert_called_with(
            self.device._device_id, # source device_id
            self.device._grid_controller_id, # target device id
            0, # current time
            self.device._current_fuel_price # fuel price
        )

    def test_for_initial_capacity(self):
        """Make sure the device has a capacity value at t = 0"""
        self.device.init()
        self.assertGreater(self.device._capacity, 0)

    def test_for_initial_capacity_broadcast(self):
        """Make sure that the capacity is sent to the grid controller at t = 0"""
        self.device.init()
        self.device._broadcast_new_capacity_callback.assert_called_with(
            self.device._device_id, # source device_id
            self.device._grid_controller_id, # target device id
            0, # current time
            self.device._current_capacity # capacity of the device
        )

    def test_fuel_level(self):
        """Test that the fuel level decreases when a load is applied"""
        self.device.init()

        # store the original fuel level
        fuel_level_orig = self.device._fuel_level

        # put a 1000 kW load on the device
        device_load = 1000000
        self.device.on_power_change(
            source_device_id=self.device._grid_controller_id,
            target_device_id=self.device._device_id,
            time=0,
            new_power=device_load
        )
        self.device.on_power_change(
            source_device_id=self.device._grid_controller_id,
            target_device_id=self.device._device_id,
            time=3600,
            new_power=0
        )

        # calculate how much should have been used
        kwh_per_gallon = self.device.get_current_generation_rate()
        gallons_used = device_load/1000.0 / kwh_per_gallon
        gallons_available = self.device._fuel_tank_capacity * (self.device._fuel_level / 100.0)
        new_gallons = gallons_available - gallons_used
        # should have used this amount of fuel
        new_fuel_level = new_gallons / self.device._fuel_tank_capacity * 100

        # update the fuel level for the device and check the results
        self.device.update_fuel_level()
        self.assertEqual(self.device._fuel_level, new_fuel_level)

    def test_make_unavailable(self):
        """Test making the power source unavailable, ie _current_capacity = 0"""
        self.device.init()
        self.device.make_unavailable()
        self.assertEqual(self.device._current_capacity, 0.0)

    def test_make_available(self):
        """Test making the power source available, ie _current_capacity > 0"""
        self.device.init()
        self.device.make_unavailable()
        self.device.make_available()
        self.assertGreater(self.device._current_capacity, 0.0)

    def test_set_power_level_unavailable(self):
        """Test setting the power level when it is unavailable (ie capacity == 0)"""
        self.device.init()
        self.device.make_unavailable()
        with self.assertRaises(Exception):
            self.device.on_power_change("gc_1", self.device.device_id, 0, 100.0)

if __name__ == "__main__":
    unittest.main()
