"""
Implements the logic used by a grid controller to calculate its price.
To use, set the price_logic_class key in the grid controller to
the name of the class, which in this case is AveragePrice
"""

from device.simulated.utility_meter import UtilityMeter

class WeightedAveragePriceLogic(object):
    """
    Calculates the average price of all available power sources,
    weighted by the fraction of power that the power source supplying
    """
    def __init__(self, power_source_manager):
        self.power_source_manager = power_source_manager

    def get_price(self):
        """Calculate the average price for all power sources"""
        numerator = 0.0
        denominator = 0.0
        power_sources = self.power_source_manager.get_available_power_sources()
        total_load = self.power_source_manager.total_load()
        if len(power_sources):
            power_sources.sort(lambda a, b: cmp(a.price, b.price))
            the_price = 0.0
            for ps in power_sources:
                if ps.load > 0 and ps.capacity > 0 and total_load > 0:
                    the_price += (ps.load / total_load) * ps.price
            if the_price < power_sources[0].price:
                # price can't be cheaper than the cheapest price
                return power_sources[0].price
            else:
                return the_price
        else:
            return None

