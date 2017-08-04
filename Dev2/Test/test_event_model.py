import unittest
from Build.supervisor import Supervisor
from Build.grid_controller import GridController
from Build.event import Event


class TestEventModel(unittest.TestCase):

    def setUp(self):
        self.sup = Supervisor()
        self.gc1 = GridController("gc1", self.sup)
        self.gc2 = GridController("gc2", self.sup)
        self.sup.register_device(self.gc1)
        self.sup.register_device(self.gc2)

    def test_power_event(self):
        self.gc1.add_event(Event(self.gc1.set_power_in, 20), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEquals(self.gc1._power_in, 20)

    """More Tests Here are Highest Priority"""