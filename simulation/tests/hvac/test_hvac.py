import unittest
from mock import MagicMock, patch
from device.simulated.hvac import Hvac

class TestHvac(unittest.TestCase):
    def setUp(self):
        config = {
            "device_id": "hvac_1",
            "cool_set_point_low": 21.0,
            "cool_set_point_high": 25.0,
            "high_set_point_low": 16.0,
            "high_set_point_high": 20.0
        }

        self.device = Hvac(config)

        self.device._grid_controller_id = "gc_1"
        self.device._broadcast_new_ttie_callback = MagicMock(name="_broadcast_new_ttie_callback")
        self.device._broadcast_new_power_callback = MagicMock(name="_broadcast_new_power_callback")
        self.device._broadcast_new_price_callback = MagicMock(name="_broadcast_new_price_callback")
        self.device._broadcast_new_capacity_callback = MagicMock(name="_broadcast_new_capacity_callback")

    def test_set_initial_events(self):
        """Test that events are scheduled after initialization"""
        self.device.init()
        # check for the set_point range event
        found = filter(lambda x: x.ttie == 3600 and x.value == "set_point_range", self.device._events)
        self.assertEqual(len(found), 1)
        # check for the reasses_setpoint event
        found = filter(lambda x: x.ttie == self.device._setpoint_reassesment_interval and x.value == "reasses_setpoint", self.device._events)
        self.assertEqual(len(found), 1)
        # check for the outdoor temperature eevent
        found = filter(lambda x: x.ttie == self.device._temperature_update_interval and x.value == "update_outdoor_temperature", self.device._events)
        self.assertEqual(len(found), 1)

    def test_initial_setpoints(self):
        """Test that the initial set points are calculated"""
        self.device.init()
        self.assertEqual(self.device._sp_cool.current_set_point, 23.0)
        self.assertEqual(self.device._sp_heat.current_set_point, 18.0)

    # def test_temperature_change(self):
        # """Test temperature changes"""
        # self.device.init()
        # print self.device._sp_cool
        # print self.device._sp_heat



if __name__ == "__main__":
    unittest.main()


