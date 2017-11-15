import unittest
from Build.supervisor import Supervisor
from Build.grid_controller import GridController
from Build.event import Event
from Build.battery import Battery
from Build.utility_meter import UtilityMeter

class TestPricingModel(unittest.TestCase):
    def setUp(self):
        self.sup = Supervisor()
        batt = Battery("batt_1", price_logic="hourly_preference", capacity=5000.0, max_charge_rate=2000.0,
                       max_discharge_rate=2000.0)
        self.gc1 = GridController(device_id="gc_1", supervisor=self.sup, battery=batt, price_logic='weighted_average')
        self.gc2 = GridController(device_id="gc_2", supervisor=self.sup, battery=batt, price_logic='weighted_average')
        self.sup.register_device(self.gc1)
        self.sup.register_device(self.gc2)
        self.gc1._connected_devices["gc_2"] = self.gc2
        self.gc2._connected_devices["gc_1"] = self.gc1

    def test_weighted_price(self):
        self.gc1.send_power_message("gc_2", -200)  # sending it out
        self.gc1.send_price_message("gc_2", 0.2)
        self.gc2.process_events()
        self.gc2.update_time(3000)
        self.gc2.modulate_price()
        print("current interval prices: {}".format(", ".join(map(str, self.gc2._price_logic.get_interval_prices()))))

if __name__ == '__main__':
    unittest.main()