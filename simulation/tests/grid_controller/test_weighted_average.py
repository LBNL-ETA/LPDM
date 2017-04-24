import unittest
from device.simulated.diesel_generator import DieselGenerator
from device.simulated.grid_controller.power_source_manager import PowerSourceManager
from device.simulated.grid_controller.price_logic import WeightedAveragePriceLogic

class TestWeightedAveragePrice(unittest.TestCase):
    """Test the average price algorithm for the grid controller"""
    def setUp(self):
        self.psm = PowerSourceManager()
        self.logic = WeightedAveragePriceLogic(power_source_manager=self.psm)

    def test_average_price(self):
        """Test the average price"""
        # add some power sources
        self.psm.add("dg_1", DieselGenerator)
        dg_1 = self.psm.get("dg_1")
        self.psm.add("dg_2", DieselGenerator)
        dg_2 = self.psm.get("dg_2")
        self.psm.add("dg_3", DieselGenerator)
        dg_3 = self.psm.get("dg_3")

        # set some price values
        self.psm.set_price("dg_1", 3.00)
        self.psm.set_price("dg_2", 2.00)
        self.psm.set_price("dg_3", 1.00)

        # this should be None because the capacity values are not set
        self.assertIsNone(self.logic.get_price())

        # set capacities for devices (devices need to have capacities set to be considered 'available')
        self.psm.set_capacity("dg_1", 1000.0)
        self.psm.set_capacity("dg_2", 1000.0)

        # average price should be 2.0 because there is no load on any device, so using the lowest price
        self.assertEqual(self.logic.get_price(), 2.0)

        # put 50% load on dg2
        dg_2.set_load(500.0)
        self.assertEqual(self.logic.get_price(), 1.0)

        # set to 100%
        dg_2.set_load(1000.0)
        self.assertEqual(self.logic.get_price(), 2.0)

        # set load of dg_1 to 50%
        dg_1.set_load(500.0)
        self.assertEqual(self.logic.get_price(), 2.0 + 1.5)


if __name__ == "__main__":
    unittest.main()

