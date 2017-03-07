import unittest
from mock import MagicMock, patch
from device.diesel_generator import GridController

class TestGridController(unittest.TestCase):
    def setUp(self):
        config = {
            "device_id": "device_1"
        }

        self.device = GridController(config)


if __name__ == "__main__":
    unittest.main()

