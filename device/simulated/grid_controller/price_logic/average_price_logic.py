"""
Implements the logic used by a grid controller to calculate its price.
To use, set the price_logic_class key in the grid controller to
the name of the class, which in this case is AveragePrice
"""

class AveragePriceLogic(object):
    """Calculates the average price of all available power sources"""
    def __init__(self, power_source_manager):
        self.power_source_manager = power_source_manager

    def get_price(self):
        """Calculate the average price for all power sources"""
        # get the power sources that have a capacity > 0
        available = self.power_source_manager.get_available_power_sources()
        # return the averge price of those devices if there are any
        return float(sum(d.price for d in available)) / len(available) if len(available) else None
