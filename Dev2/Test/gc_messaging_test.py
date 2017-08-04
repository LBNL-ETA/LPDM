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

    def test_GC_register_message(self):
        self.gc1.add_event(Event(self.gc1.on_allocated, "gc2", 20), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEqual(self.gc1._allocated["gc2"], 20)

    def test_GC_power_message(self):
        self.gc1.add_event(Event(self.gc1.on_allocated, "gc2", 20), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEqual(self.gc1._allocated["gc2"], 20)


    """
    def test_engage(self):
        self.gc2.engage([self.gc1])  # informs GC1 that GC2 exists.
        self.assertEquals("gc1" in self.gc1._connected_devices.keys())
    """

if __name__ == '__main__':
    unittest.main()