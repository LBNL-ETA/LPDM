import logging
from device.base.power_source import PowerSource
from device.simulated.battery import Battery
from power_source_item import PowerSourceItem
from simulation_logger import message_formatter

class PowerSourceManager(object):
    def __init__(self):
        self.power_sources = []
        self.logger = logging.getLogger("lpdm")
        self._device_id = "power_source_manager"
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
        """Register a power source"""
        # make sure the type of object added is a power source
        if not issubclass(DeviceClass, PowerSource):
            raise Exception("The PowerSourceManager can only accepts PowerSource devices.")

        # make sure a device with the same id does not exist
        found = filter(lambda d: d.device_id == device_id, self.power_sources)
        if len(found) == 0:
            self.power_sources.append(PowerSourceItem(device_id, DeviceClass, device_instance))
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
                    message="set capacity from {}".format(device_id),
                    tag="set_capacity".format(device_id),
                    value=capacity
                )
            )
            self.logger.debug(
                self.build_message(
                    message="total capacity",
                    tag="total_capacity",
                    value=self._capacity
                )
            )

    def set_price(self, device_id, price):
        """set the price of electricity for a power source"""
        d = self.get(device_id)
        d.price = price

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

    def total_capacity(self):
        """calculate the total capacity for all power sources"""
        # return sum(d.capacity for d in self.power_sources if d.is_available())
        return self._capacity

    def total_load(self):
        """calculate the total load on all the power sources"""
        # return sum(d.load for d in self.power_sources)
        return self._load

    def output_capacity(self):
        """Calculate the output capacity (total_load / total_capaacity)"""
        return self._load / self._capacity if self._capacity else None

    def can_handle_load(self, new_load):
        """Is there enough capacity to handle the load?"""
        return (self._load + new_load) <= self.total_capacity()

    def has_available_power_sources(self):
        """Are there powersources configured and available for use?"""
        return True if len([p for p in self.power_sources if p.is_available()]) else False

    def add_load(self, new_load):
        """
        Add load to the various power sources
        """
        self._load += new_load

    def remove_load(self, new_load):
        """Remove load from the system"""
        self.add_load(-1.0 * new_load)

    def update_rechargeable_items(self):
        """Update the status of rechargeable items"""
        for p in self.power_sources:
            if p.DeviceClass is Battery and p.device_instance:
                # update the battery (direct connect)
                p.device_instance.update_status()

    def optimize_load(self):
        """
        Check that the loads are optimally distributed among the power sources.
        Move load from the more expensive power sources to the cheaper ones.
        """
        # self.logger.debug(self.build_message(message="optimize_load (load = {}, cap = {})".format(self._load, self._capacity), tag="optimize_before"))
        # update the status of rechargeable itmes
        self.update_rechargeable_items()
        # self.logger.debug(self.build_message(message="optimize_load-2 (load = {}, cap = {})".format(self._load, self._capacity), tag="optimize_before"))
        # get the current total load on the system
        original_load = self._load
        # add the new load
        remaining_load = original_load
        starting_load = remaining_load
        # self.logger.debug(self.build_message("begin optimizing load {}".format(remaining_load)))
        # if original_load == 0 and remaining_load == 0:
            # # no need to do anything if there's no load
            # return

        # get the power sources and sort by the cheapest price
        power_sources = [p for p in self.power_sources if p.is_configured()]
        power_sources = sorted(power_sources, lambda a, b: cmp(a.price, b.price))
        for ps in power_sources:
            # how much power is available for the device
            if remaining_load == 0:
                # no more load left to distribute, remove power
                ps.set_load(0.0)
            else:
                # there is power available for this device and power left to distribute
                if not ps.is_available():
                    if ps.load > 0:
                        # self.logger.debug(self.build_message(message="set load for {} to {}".format(ps, 0)))
                        ps.set_load(0.0)
                else:
                    if remaining_load > ps.capacity:
                        # can't put all the remaining load on this power source
                        # set to 100% and try the next power source
                        if ps.load != ps.capacity:
                            # self.logger.debug(self.build_message(message="set load for {} to {}".format(ps, ps.capacity)))
                            ps.set_load(ps.capacity)
                        remaining_load -= ps.capacity
                    else:
                        # this power source can handle all of the remaining load
                        # self.logger.debug(self.build_message(message="set load for {} to {}".format(ps, remaining_load)))
                        if ps.load != remaining_load:
                            ps.set_load(remaining_load)
                        remaining_load = 0

        diff = abs(starting_load - self._load)
        if remaining_load > 1e-7:
            self.logger.debug(
                self.build_message(
                    message="Unable to handle the load, total_load = {}, total_capacity = {}".format(self.total_load(), self.total_capacity()))
            )
            return False
        elif diff > 1e-7:
            # compare the difference being below some threshhold instead of equality
            self.logger.debug(self.build_message(message="starting load = {}, total_load = {}, equal ? {}".format(starting_load, self._load, abs(starting_load - self._load))))
            raise Exception("starting/ending loads do not match {} != {}".format(starting_load, self._load))
        # self.logger.debug(self.build_message(message="optimize_load (load = {}, cap = P{})".format(self._load, self._capacity), tag="optimize_after"))
        self.logger.debug(
            self.build_message(
                message="total load",
                tag="total_load",
                value=self.total_load()
            )
        )
        # self.logger.debug(
            # self.build_message(
                # message="total capacity",
                # tag="total_capacity",
                # value=self.total_capacity()
            # )
        # )
        return True

    def get_available_power_sources(self):
        """get the power sources that have a non-zero capacity"""
        return filter(lambda d: d.is_available(), self.power_sources)

    def get_changed_power_sources(self):
        """return a list of powersources that have been changed"""
        return [p for p in self.power_sources if p.load_changed]

    def reset_changed(self):
        """Reset all the changed flags on all power sources"""
        [p.reset_changed() for p in self.power_sources]

