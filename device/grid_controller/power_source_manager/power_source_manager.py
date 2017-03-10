import logging
from device.power_source import PowerSource
from power_source_item import PowerSourceItem

class PowerSourceManager(object):

    def __init__(self):
        self.power_sources = []
        self.logger = logging.getLogger("lpdm")

    def count(self):
        """Return the number of power sources connected"""
        return len(self.power_sources)

    def add(self, device_id, DeviceClass):
        """Register a power source"""
        # make sure the type of object added is a power source
        if not issubclass(DeviceClass, PowerSource):
            raise Exception("The PowerSourceManager can only accepts PowerSource devices.")

        # make sure a device with the same id does not exist
        found = filter(lambda d: d.device_id == device_id, self.power_sources)
        if len(found) == 0:
            self.power_sources.append(PowerSourceItem(device_id, DeviceClass))
            self.logger.debug("message: registered a power source {} - {}".format(device_id, DeviceClass))
        else:
            raise Exception("The device_id already exists {}".format(device_id))

    def set_capacity(self, device_id, capacity):
        """set the capacity for a power source"""
        d = self.get(device_id)
        if d.load <= capacity:
            d.capacity = capacity
        else:
            raise Exception(
                "Attempt to set the capacity for a power source that is less than the load ({} > {})".format(d.load, capacity)
            )

    def set_price(self, device_id, price):
        """set the price of electricity for a power source"""
        d = self.get(device_id)
        d.price = price
        self.logger.debug("message: power_source_manager set price for device {} to {}".format(device_id, price))

    def set_load(self, device_id, load):
        """set the load for a power source"""
        d = self.get(device_id)
        if load <= d.capacity:
            d.load = load
        else:
            raise Exception(
                "Attempt to set the load for a power source that is greater than capacity ({} > {})".format(load, d.capacity)
            )

    def get(self, device_id):
        """Get the info for a power source by its ID"""
        found = filter(lambda d: d.device_id == device_id, self.power_sources)
        self.logger.debug("message: found power source {}".format(found))
        if len(found) == 1:
            return found[0]
        else:
            raise Exception("An error occured trying to retrieve the power source {}".format(device_id))

    def total_capacity(self):
        """calculate the total capacity for all power sources"""
        return sum(d.capacity for d in self.power_sources if not d.capacity is None)

    def get_available_power_sources(self):
        """get the power sources that have a non-zero capacity"""
        return filter(lambda d: d.capacity > 0 and not d.price is None, self.power_sources)
