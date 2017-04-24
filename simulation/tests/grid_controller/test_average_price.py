import unittest
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.grid_controller.power_source_manager import PowerSourceManager
from device.simulated.grid_controller.price_logic import AveragePriceLogic

class TestAveragePrice(unittest.TestCase):
    """Test the average price algorithm for the grid controller"""
    def setUp(self):
        self.psm = PowerSourceManager()
        self.logic = AveragePriceLogic(power_source_manager=self.psm)

    def test_average_price(self):
        """Test the average price"""
        # add some power sources
        self.psm.add("dg_1", DieselGenerator)
        self.psm.add("dg_2", DieselGenerator)
        self.psm.add("dg_3", DieselGenerator)

        # set some price values
        self.psm.set_price("dg_1", 1.00)
        self.psm.set_price("dg_2", 2.00)
        self.psm.set_price("dg_3", 3.00)

        # this should be None because the capacity values are not set
        self.assertIsNone(self.logic.get_price())

        # set capacities for devices (devices need to have capacities set to be considered 'available')
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)

        # average price is 1.5 because dg_3 doesn't have a capacity > 0
        self.assertEqual(self.logic.get_price(), 1.5)


if __name__ == "__main__":
    unittest.main()
