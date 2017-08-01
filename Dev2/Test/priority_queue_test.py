import unittest
from Build import priority_queue


class TestPriorityQueue(unittest.TestCase):


    def setUp(self):
        self.pq = priority_queue.PriorityQueue()

    def tearDown(self):
        self.pq.clear()

    def test_is_empty(self):
        self.assertTrue(self.pq.is_empty())

    def test_is_empty_false(self):
        self.pq.add("one", 1)
        self.assertFalse(self.pq.is_empty())

    def test_pop(self):
        self.pq.add("three", 3)
        self.pq.add("one", 1)
        self.pq.add("two", 2)
        self.assertEqual(self.pq.pop(), ("one", 1))
        self.assertEqual(self.pq.pop(), ("two", 2))
        self.assertEqual(self.pq.pop(), ("three", 3))
        self.assertTrue(self.pq.is_empty())

    def test_peek(self):
        self.pq.add("one", 1)
        self.assertEqual(self.pq.peek(), ("one", 1))
        self.assertFalse(self.pq.is_empty())

    def test_shift(self):
        self.pq.add("three", 3)
        self.pq.add("one", 1)
        self.pq.add("two", 2)
        self.pq.shift(1)
        self.assertEqual(self.pq.pop(), ("one", 0))
        self.assertEqual(self.pq.pop(), ("two", 1))
        self.assertEqual(self.pq.pop(), ("three", 2))
        self.assertTrue(self.pq.is_empty())

    def test_updating_values(self):
        self.pq.add("a", 3)
        self.pq.add("c", 1)
        self.pq.add("b", 2)
        self.pq.add("c", 5)
        self.pq.add("b", 0)
        self.assertEqual(self.pq.pop(), ("b", 0))
        self.assertEqual(self.pq.pop(), ("a", 3))
        self.assertEqual(self.pq.pop(), ("c", 5))

if __name__ == '__main__':
    unittest.main()