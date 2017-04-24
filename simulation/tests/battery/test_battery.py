import unittest
from mock import MagicMock, patch, call
from device.simulated.grid_controller import GridController
from device.simulated.battery import Battery
from device.simulated.battery.lpdm_exception import LpdmMissingPowerSourceManager, LpdmBatteryDischargeWhileCharging, \
        LpdmBatteryNotDischarging
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.grid_controller.price_logic import AveragePriceLogic
from device.simulated.eud import Eud

class TestBattery(unittest.TestCase):
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
        # set a reference to the battery
        self.battery = self.gc._battery

        # add devices
        self.gc.add_device("eud_1", Eud)
        self.gc.add_device("dg_1", DieselGenerator)

    def test_battery_exists(self):
        """Test if the battery exists within the grid controller"""
        self.assertIsNotNone(self.battery)

    def test_battery_raises_missing_psm(self):
        """Test that the battery will raise an exception if a power source manager is not present"""
        self.battery = None
        self.battery = Battery(self.battery_config)
        with self.assertRaises(LpdmMissingPowerSourceManager):
            self.battery.update_status()

    def test_battery_has_price(self):
        """Test the battery's price shows up"""
        d = self.gc.power_source_manager.get(self.battery_config["device_id"])
        self.assertEqual(d.price, self.battery_config["price"])
        self.assertEqual(self.battery._price, self.battery_config["price"])

    def test_battery_has_capacity(self):
        """Test the battery's price capacity up"""
        d = self.gc.power_source_manager.get(self.battery_config["device_id"])
        self.assertEqual(d.capacity, self.battery_config["capacity"])
        self.assertEqual(self.battery._capacity, self.battery_config["capacity"])

    def test_events_shared(self):
        """Test that the grid controller's event list is the same as the battery's event list"""
        self.assertIs(self.gc._events, self.battery._events)

    def test_battery_has_update_status_event(self):
        """Test that the battery_status event has been set after initialization"""
        self.assertEqual(len(self.gc._events), 1)
        self.assertEqual(len(self.battery._events), 1)

    def test_discharge(self):
        """
        Test if the battery is ok to discharge.
        Should initially be able to discharge at t=0
        """
        # set up an additional power source
        self.gc.power_source_manager.set_price('dg_1', 0.3)
        self.gc.power_source_manager.set_capacity('dg_1', 2000.0)

        # update the battery status
        # should be true
        self.assertTrue(self.battery._can_discharge)
        # add load to the gc
        eud_1 = self.gc.power_source_manager.get("eud_1")
        self.gc.on_power_change('eud_1', 'gc_1', 0, 100.0)
        self.assertEqual(self.gc.power_source_manager.total_load(), 100)
        # self.gc.power_source_manager.optimize_load()

        # set the load on the battery to what the PSM says the battery is using
        bt = self.gc.power_source_manager.get("bt_1")
        self.battery.set_load(bt.load)

        # move time forward 55 minutes
        self.battery.set_time(60.0 * 55.0)
        self.battery.process_events()
        # load and capacity both at 100 W, soc after 55 minutes should be equal to 1 - 55/60
        self.assertAlmostEqual(self.battery._current_soc, 1.0 - 55.0/60.0)
        # since this is below the min_soc it should be unable to discharge and triggered to charge
        self.assertFalse(self.battery._can_discharge)
        self.assertTrue(self.battery._can_charge)

    def test_charge(self):
        """Test that the battery can_charge flag will be set to True"""
        # set up an additional power source
        self.gc.power_source_manager.set_price('dg_1', 0.3)
        self.gc.power_source_manager.set_capacity('dg_1', 2000.0)

        # add load to the gc
        eud_1 = self.gc.power_source_manager.get("eud_1")
        self.gc.on_power_change('eud_1', 'gc_1', 0, 100.0)
        # self.gc.power_source_manager.optimize_load()

        # set the load on the battery to what the PSM says the battery is using
        bt = self.gc.power_source_manager.get("bt_1")
        self.battery.set_load(bt.load)

        # move time forward 55 minutes
        # this should move the state of charge below the minimum to enable charging
        self.battery.set_time(self.battery._time + 60.0 * 55.0)
        self.battery.process_events()
        # load and capacity both at 100 W, soc after 55 minutes should be equal to 1 - 55/60
        self.assertAlmostEqual(self.battery._current_soc, 1.0 - 55.0/60.0)
        # since this is below the min_soc it should be unable to discharge and triggered to charge
        self.assertFalse(self.battery._can_discharge)
        self.assertTrue(self.battery._can_charge)

        # setup the next update status event
        self.battery.schedule_next_events()

        # move forward another 50 minutes
        # at a max charge rate of 100 W
        starting_soc = self.battery._current_soc
        starting_time = self.battery._time
        self.battery.set_time(self.battery._time + 60.0 * 55.0)
        self.battery.process_events()
        # calculate what the soc should now be based on the starting soc and time difference
        new_soc = ((self.battery._capacity * starting_soc) + \
                (self.battery.charge_rate() * (self.battery._time - starting_time) / 3600.0)) / self.battery._capacity
        self.assertAlmostEqual(new_soc, self.battery._current_soc)

    def test_state_of_charge(self):
        """Test the state of charge calculation"""
        # set up an additional power source
        self.gc.power_source_manager.set_price('dg_1', 0.3)
        self.gc.power_source_manager.set_capacity('dg_1', 2000.0)

        # add load to the gc
        eud_1 = self.gc.power_source_manager.get("eud_1")
        self.gc.on_power_change('eud_1', 'gc_1', 0, 100.0)
        self.assertEqual(self.gc.power_source_manager.total_load(), 100)
        # self.gc.power_source_manager.optimize_load()
        # set the load on the battery to what the PSM says the battery is using
        bt = self.gc.power_source_manager.get("bt_1")
        self.battery.set_load(bt.load)
        # make sure the load is correct
        self.assertEqual(bt.load, 100.0)
        self.assertEqual(self.battery._load, 100.0)
        # move time forward 1 hour, which should set the soc to 0 since capacity was set to 100W
        self.battery.set_time(3600)
        self.battery.process_events()
        self.assertEqual(self.battery._current_soc, 0)


if __name__ == "__main__":
    unittest.main()
