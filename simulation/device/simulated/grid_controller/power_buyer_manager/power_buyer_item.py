class PowerBuyerItem:
    def __init__(self, device_id, DeviceClass, device_instance=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.capacity = None
        self.load = 0.0
        self.price = None
        self.price_threshold = None
        self.device_instance = device_instance

        self.capacity_changed = False
        self.load_changed = False

    def __repr__(self):
        return "id: {}, class: {}, capacity: {}, load: {}, price: {}, price_threshold: {}".format(
            self.device_id,
            self.DeviceClass,
            self.capacity,
            self.load,
            self.price,
            self.price_threshold
        )

    def update_status(self):
        if not self.device_instance is None:
            self.device_instance.update_status()

    def is_configured(self):
        """Is this power source configured? ie has capacity and price been set?"""
        return self.is_available()

    def is_available(self):
        """Is this power source configured? ie has capacity and price been set?"""
        return not self.capacity is None and not self.price_threshold is None

    def set_load(self, load):
        """
        Set the load for the power source.
        In the context of a a power buyer, the load would be how much power the device is buying
        """
        if load > 0 and not self.is_available():
            raise Exception("Attempted to put load of {} on a power source that has not been configured.".format(load))
        if load != self.load:
            self.load_changed = True
            self.load = load
        # if there's an actual device instance connected then set that load as well
        if self.device_instance:
            self.device_instance.set_load(load)

    def set_capacity(self, capacity):
        """
        Set the capacity for the power source.
        In the context of a power buyer, the capacity would be the max amount of power a device can purchase
        """
        if capacity != self.capacity:
            self.capacity_changed = True
            self.capacity = capacity
        # if self.load > self.capacity:
            # raise Exception("Load > capacity ({} > {})".format(self.load, self.capacity))

    def set_price_threshold(self, price_threshold):
        """Set the price threshold for power buyback for the device"""
        if self.price_threshold != price_threshold:
            self.price_threshold = price_threshold
            self.price_threshold_changed = True

    def has_changed(self):
        """Has this power source been changed"""
        return self.capacity_changed or self.load_changed or self.price_threshold_changed

    def reset_changed(self):
        """Set the load/capacity changed flags to False"""
        self.capacity_changed = False
        self.load_changed = False
        self.price_threshold_changed = False

