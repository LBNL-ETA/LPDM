import logging

class PowerSourceItem:
    def __init__(self, device_id, DeviceClass, capacity=None, load=None, price=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.capacity = None
        self.load = 0.0
        self.price = None

        self.capacity_changed = False
        self.load_changed = False

        self.logger = logging.LoggerAdapter(logging.getLogger("lpdm"), {"sim_seconds": "", "device_id": "psi"})

    def __repr__(self):
        return "id: {}, class: {}, capacity: {}, load: {}, price: {}".format(
            self.device_id,
            self.DeviceClass,
            self.capacity,
            self.load,
            self.price
        )

    def is_configured(self):
        """Is this power source configured? ie has capacity and price been set?"""
        return not self.capacity is None and not self.price is None

    def is_available(self):
        """Is this power source configured? ie has capacity and price been set?"""
        return self.is_configured() and self.capacity > 0

    def can_handle_load(self, new_load):
        """Can this power souce handle the additional load?"""
        if self.capacity is None:
            raise Exception("The capacity for {} has not been set.".format(self.device_id))
        if self.price is None:
            raise Exception("The price for {} has not been set.".format(self.device_id))
        return (self.load + new_load) <= self.capacity

    def add_load(self, new_load):
        """Add additional load to the power source"""
        if self.can_handle_load(new_load):
            self.set_load(self.load + new_load)
            self.logger.debug("message: Add load {}".format(new_load))
            self.logger.debug("message: Total load {}".format(self.load))
            return True
        else:
            return False

    def set_load(self, load):
        """
        Set the load for the power source.
        Also set a boolean flag indicating the load has changed.
        """
        if load > 0 and not self.is_available():
            raise Exception("Attempted to put load of {} on a power source that has not been configured.".format(load))
        if load != self.load:
            self.load_changed = True
        self.load = load

    def set_capacity(self, capacity):
        """
        Set the capacity for the power source.
        Also set a boolean flag indicating the capacity has changed.
        """
        if capacity != self.capacity:
            self.capacity_changed = True
            self.capacity = capacity
        # if self.load > self.capacity:
            # raise Exception("Load > capacity ({} > {})".format(self.load, self.capacity))

    def reset_changed(self):
        """Set the load/capacity changed flags to False"""
        self.capacity_changed = False
        self.load_changed = False
