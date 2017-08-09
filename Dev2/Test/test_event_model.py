import unittest
from Build.supervisor import Supervisor
from Build.grid_controller import GridController
from Build.event import Event
from Build.priority_queue import PriorityQueue

class TestEventModel(unittest.TestCase):

    def setUp(self):
        self.sup = Supervisor()
        self.gc1 = GridController("gc1", self.sup)
        self.gc2 = GridController("gc2", self.sup)
        self.sup.register_device(self.gc1)
        self.sup.register_device(self.gc2)

    def test_event_queue(self):
        pq = PriorityQueue()
        pq.add(Event(self.gc1.set_power_in, 20), 1)
        pq.add(Event(self.gc1.set_power_in, 20), 2) # to make sure they are treated as distinct entities.
        event1, time_stamp = pq.pop()
        event1.run_event()
        self.assertEqual(self.gc1._power_in, 20)
        event2, time_stamp = pq.pop()
        event2.run_event()
        self.assertEqual(self.gc1._power_in, 20)

    def test_single_argument_event(self):
        self.gc1.add_event(Event(self.gc1.set_power_in, 20), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEqual(self.gc1._power_in, 20)

    def test_multiple_argument_event(self):
        self.gc1.add_event(Event(self.gc1.on_allocated, "gc2", 20), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEqual(self.gc1._allocated["gc2"], 20)

    def test_no_argument_event(self):
        self.gc1.add_event(Event(self.gc1.add_power_in), 1)
        self.gc1.update_time(1)
        self.gc1.process_events()
        self.assertEqual(self.gc1._power_in, 10)

    """More Tests Here are Highest Priority"""

if __name__ == '__main__':
    unittest.main()
