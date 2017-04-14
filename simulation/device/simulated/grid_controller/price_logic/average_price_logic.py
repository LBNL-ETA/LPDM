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
        if len(available):
            available.sort(lambda a, b: cmp(a.price, b.price))
            total = 0.0
            n = 0
            for p in available:
                if p.load > 0:
                    total += p.price
                    n += 1
            # return the averge price of those devices if there are any
            return total/n if n else available[0]
        else:
            return None
