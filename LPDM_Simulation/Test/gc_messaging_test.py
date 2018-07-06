import unittest

from Build.Objects.battery import Battery
from Build.Objects.grid_controller import GridController
from Build.Simulation_Operation.supervisor import Supervisor


@unittest.skip("TODO: DO NOT USE. HAS NOT BEEN UPDATED.")
class TestGCMessaging(unittest.TestCase):
    def setUp(self):
        self.sup = Supervisor()
        self.gc1 = GridController("gc1", self.sup)
        self.gc2 = GridController("gc2", self.sup)
        self.sup.register_device(self.gc1)
        self.sup.register_device(self.gc2)
        self.gc1._connected_devices["gc2"] = self.gc2

    def test_GC_register_message(self):
        self.gc1.send_register_message("gc2", 1)
        while self.sup.has_next_event():
            self.sup.occur_next_event()
        self.assertEqual(self.gc2._connected_devices["gc1"], self.gc1)

    def test_GC_power_message_unfulfilled(self):
        # no battery. Can't provide, lists every as request.
        self.gc2._connected_devices["gc1"] = self.gc1
        self.gc1.send_power_message("gc2", 10)
        while self.sup.has_next_event():
            self.sup.occur_next_event()
        self.assertEqual(self.gc2._requested["gc1"], -10)

    def test_balance_power_below_max_battery_rate(self):
        self.gc2._connected_devices["gc1"] = self.gc1
        batt1 = Battery(None)  # no price logic
        batt2 = Battery(None)  # no price logic.
        self.gc1._battery = batt1
        self.gc2._battery = batt2
        self.gc1.send_power_message("gc2", 70)
        while self.sup.has_next_event():
            self.sup.occur_next_event()
        self.assertEqual(self.gc2._loads["gc1"], -70)
        self.assertEqual(self.gc2._battery.get_load(), -70)

    def test_balance_power_above_max_battery_rate(self):
        self.gc1.send_register_message("gc2", 1)
        batt1 = Battery(None)  # no price logic
        batt2 = Battery(None)  # no price logic.
        self.gc1._battery = batt1
        self.gc2._battery = batt2
        self.gc1.send_power_message("gc2", 110)
        while self.sup.has_next_event():
            self.sup.occur_next_event()
        self.assertEqual(self.gc2._loads["gc1"], -100) # 100 is default max charge rate.
        self.assertEqual(self.gc2._battery.get_load(), -100)
        self.assertEqual(self.gc2._requested["gc1"], -10) # 10 remaining to be sold to ya.

        """
        Remaining Tests: Do one with utility meter.
        """


if __name__ == '__main__':
    unittest.main()
