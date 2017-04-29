import logging
from device.base.power_source_buyer import PowerSourceBuyer
from power_buyer_item import PowerBuyerItem
from simulation_logger import message_formatter

class PowerBuyerManager(object):
    def __init__(self):
        self.power_sources = []
        self.logger = logging.getLogger("lpdm")
        self._device_id = "power_buyer_manager"
        self._load = 0.0
        self._capacity = 0.0
        self._time = 0

    def __repr__(self):
        return "Load->{}, Capacity->{}".format(
            self._load,
            self._capacity
        )

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=self._time,
            device_id=self._device_id
        )

    def set_time(self, new_time):
        self._time = new_time

    def shutdown(self):
        """remove load from all power sources"""
        [p.set_load(0.0) for p in self.power_sources]
        self._load = 0.0

    def count(self):
        """Return the number of power sources connected"""
        return len(self.power_sources)

    def add(self, device_id, DeviceClass, device_instance=None):
        """Register a power buyer"""
        # make sure the type of object added is a power source
        if not issubclass(DeviceClass, PowerSourceBuyer):
            raise Exception("The PowerBuyerManager can only accepts PowerSourceBuyer devices.")

        # make sure a device with the same id does not exist
        found = filter(lambda d: d.device_id == device_id, self.power_sources)
        if len(found) == 0:
            self.power_sources.append(PowerBuyerItem(device_id, DeviceClass, device_instance))
        else:
            raise Exception("The device_id already exists {}".format(device_id))

    def set_capacity(self, device_id, capacity):
        """set the capacity for a power source"""
        if not capacity is None:
            d = self.get(device_id)
            diff = capacity - d.capacity if not d.capacity is None else capacity
            d.set_capacity(capacity)
            self._capacity += diff
            if abs(self._capacity) < 1e-7:
                self._capacity = 0
            self.logger.debug(
                self.build_message(
                    message="set max buy capacity from {}".format(device_id),
                    tag="set_max_buy_capacity".format(device_id),
                    value=capacity
                )
            )
            self.logger.debug(
                self.build_message(
                    message="total buy capacity",
                    tag="total_buy_capacity",
                    value=self._capacity
                )
            )

    def set_price(self, device_id, price):
        """set the price of electricity for a power source"""
        d = self.get(device_id)
        d.price = price

    def set_price_threshold(self, device_id, price_threshold):
        """set the price threshold for buying back power"""
        d = self.get(device_id)
        d.set_price_threshold(price_threshold)

    def set_load(self, device_id, load):
        """set the load for a specific power source"""
        d = self.get(device_id)
        if load > 0 and not d.is_available():
            raise Exception("The power source {} has not been configured".format(device_id))

        if load <= d.capacity:
            d.set_load(load)
        else:
            raise Exception(
                "Attempt to set the load for a power source that is greater than capacity ({} > {})".format(load, d.capacity)
            )

    def get(self, device_id=None):
        """Get the info for a power source by its ID"""
        if device_id is None:
            # return all devices
            return self.power_sources
        else:
            found = filter(lambda d: d.device_id == device_id, self.power_sources)
            if len(found) == 1:
                return found[0]
            else:
                return None

    def get_buyers(self):
        """Get the devices that are currently purchasing power"""
        return [p for p in self.power_sources if p.load > 0]

    def total_capacity(self):
        """calculate the total capacity for all power sources"""
        # return sum(d.capacity for d in self.power_sources if d.is_available())
        return self._capacity

    def total_load(self):
        """calculate the total load on all the power sources"""
        # return sum(d.load for d in self.power_sources)
        return self._load

    def get_available_power_sources(self):
        """get the power sources that have a non-zero capacity"""
        return filter(lambda d: d.is_available(), self.power_sources)

    def get_changed_power_sources(self):
        """return a list of powersources that have been changed"""
        return [p for p in self.power_sources if p.load_changed]

    def reset_changed(self):
        """Reset all the changed flags on all power sources"""
        [p.reset_changed() for p in self.power_sources]


