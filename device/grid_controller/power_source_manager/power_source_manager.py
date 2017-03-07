import logging

class PowerSourceItem:
    def __init__(self, device_id, DeviceClass, capacity=None, load=None, price=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.capacity = 0.0
        self.load = 0.0
        self.price = 0.0

class PowerSourceManager(object):

    def __init__(self):
        self.power_sources = []
        self.logger = logging.getLogger("lpdm")

    def count(self):
        """Return the number of power sources connected"""
        return len(self.power_sources)

    def add(self, device_id, DeviceClass):
        """Register a power source"""
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

    def set_load(device_id, load):
        """set the load for a power source"""
        d = self.get(device_id)
        if load <= capacity:
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
