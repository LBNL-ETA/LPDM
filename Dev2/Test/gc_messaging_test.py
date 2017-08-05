import unittest
from Build.supervisor import Supervisor
from Build.grid_controller import GridController
from Build.event import Event


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

    def test_GC_power_message(self):
        self.gc2._connected_devices["gc1"] = self.gc1
        self.gc1.send_power_message("gc2", 10)
        while self.sup.has_next_event():
            self.sup.occur_next_event()
        self.assertEqual(self.gc2._loads["gc1"], -10)

if __name__ == '__main__':
    unittest.main()