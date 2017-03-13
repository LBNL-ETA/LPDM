import logging

class PowerSourceItem:
    def __init__(self, device_id, DeviceClass, capacity=None, load=None, price=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.capacity = None
        self.load = 0.0
        self.price = None
        self.logger = logging.getLogger("lpdm")

    def is_configured(self):
        """Is this power source configured? ie has capacity and price been set?"""
        return not self.capacity is None and not self.price is None

    def can_handle_load(self, new_load):
        """Can this power souce handle the additional load?"""
        if self.capacity is None:
            raise Exception("The capacity for {} has not been set.".format(self.device_id))
        if self.price is None:
            raise Exception("The price for {} has not been set.".format(self.device_id))
        return (self.load + new_load) < self.capacity

    def add_load(self, new_load):
        """Add additional load to the power source"""
        if self.can_handle_load(new_load):
            self.load += new_load
            self.logger.debug("message: Add load {}".format(new_load))
            self.logger.debug("message: Total load {}".format(self.load))
            return True
        else:
            return False
