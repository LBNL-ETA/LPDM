import unittest
from Build.supervisor import Supervisor
from Build.grid_controller import GridController

# TODO: DO NOT USE. HAS NOT BEEN UPDATED.

class TestDeviceRegister(unittest.TestCase):
    def setUp(self):
        self.sup = Supervisor()
        self.gc1 = GridController("gc1", self.sup)
        self.gc2 = GridController("gc2", self.sup, [self.gc1])
        self.sup.register_device(self.gc1)
        self.sup.register_device(self.gc2)
        self.gc1.register_device(self.gc2, self.gc2.get_id(), 1)

    def test_connections(self):
        self.assertEqual(self.gc1._connected_devices["gc2"], self.gc2)
        self.assertEqual(self.gc2._connected_devices["gc1"], self.gc1)


