import unittest
from mock import MagicMock, patch, call
from device.simulated.grid_controller import GridController
from device.simulated.battery import Battery
from device.simulated.battery.lpdm_exception import LpdmMissingPowerSourceManager
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.grid_controller.price_logic import AveragePriceLogic
from device.simulated.eud import Eud

class TestBatteryInGridController(unittest.TestCase):
    def setUp(self):
        self.battery_config = {
            "device_id": "bt_1",
            "capacity": 100.0,
            "price": 0.0,
            "min_soc": 0.2,
            "max_soc": 0.8,
            "max_charge_rate": 100.0,
            "check_soc_rate": 300,
            "current_soc": 1.0
        }
        config = {
            "device_id": "gc_1",
            "battery": self.battery_config
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

    def test_battery_exists(self):
        """Test if the battery exists within the grid controller"""
        self.assertIsNotNone(self.gc._battery)

    def test_battery_has_device_id(self):
        """Test that the device_id is set"""
        self.assertEqual(self.gc._battery._device_id, self.battery_config["device_id"])

    def test_battery_raises_missing_psm(self):
        """Test that the battery will raise an exception if a power source manager is not present"""
        self.gc._battery = None
        self.gc._battery = Battery(self.battery_config)
        with self.assertRaises(LpdmMissingPowerSourceManager):
            self.gc._battery.update_status()

    def test_battery_has_price(self):
        """Test the battery's price shows up"""
        d = self.gc.power_source_manager.get(self.battery_config["device_id"])
        self.assertEqual(d.price, self.battery_config["price"])
        self.assertEqual(self.gc._battery._price, self.battery_config["price"])

    def test_battery_has_capacity(self):
        """Test the battery's price capacity up"""
        d = self.gc.power_source_manager.get(self.battery_config["device_id"])
        self.assertEqual(d.capacity, self.battery_config["capacity"])
        self.assertEqual(self.gc._battery._capacity, self.battery_config["capacity"])

    def test_events_shared(self):
        """Test that the grid controller's event list is the same as the battery's event list"""
        self.assertIs(self.gc._events, self.gc._battery._events)

    def test_battery_has_update_status_event(self):
        """Test that the battery_status event has been set after initialization"""
        self.assertEqual(len(self.gc._events), 1)
        self.assertEqual(len(self.gc._battery._events), 1)

    def test_initial_soc(self):
        """Test that the initial state of charge"""
        self.assertEqual(self.gc._battery._current_soc, 1.0)

    def test_battery_load(self):
        """Test that the battery will accept load"""
        # set up an additional power source
        self.gc.power_source_manager.set_price('dg_1', 0.3)
        self.gc.power_source_manager.set_capacity('dg_1', 2000.0)

        # add load to the gc
        eud_1 = self.gc.device_manager.get("eud_1")
        self.gc.on_power_change('eud_1', 'gc_1', 0, 100.0)
        self.assertEqual(self.gc.power_source_manager.total_load(), 100)
        self.assertEqual(eud_1.load, 100.0)

        # the battery should be set to discharge
        self.assertTrue(self.gc._battery._can_discharge)

        # the initial state of the battery is such that it should be able to handle load
        self.assertEqual(self.gc._battery._load, 100.0)

        # move time forward to drain the battery so it will start charging
        # this should move the state of charge below the minimum to enable charging
        self.gc.on_time_change(self.gc._time + 60.0 * 55.0)
        # load and capacity both at 100 W, soc after 55 minutes should be equal to 1 - 55/60
        self.assertAlmostEqual(self.gc._battery._current_soc, 1.0 - 55.0/60.0)
        # since this is below the min_soc it should be unable to discharge and triggered to charge
        self.assertFalse(self.gc._battery._can_discharge)
        self.assertTrue(self.gc._battery._can_charge)

        # check the load on the generator, should be eud + battery charge
        dg = self.gc.power_source_manager.get("dg_1")
        self.assertEqual(dg.load, self.gc._battery.charge_rate() + eud_1.load)

        # move forward in time to finish battery charge
        # battery should be finished charging
        # so load should just be the 100 W eud
        # self.gc._battery.set_time(self.gc._battery._time + 60.0 * 55.0)
        # self.gc._battery.process_events()
        self.gc.on_time_change(self.gc._time + 60.0 * 55.0)
        bt = self.gc.power_source_manager.get("bt_1")
        self.assertEqual(bt.load, 100)
        self.assertEqual(self.gc.power_source_manager.total_load(), 100)


if __name__ == "__main__":
    unittest.main()

