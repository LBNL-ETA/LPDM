import logging
from device.power_source import PowerSource
from power_source_item import PowerSourceItem
from simulation_logger import message_formatter

class PowerSourceManager(object):
    def __init__(self):
        self.power_sources = []
        self.logger = logging.getLogger("lpdm")
        self._device_id = "power_source_manager"

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=None,
            device_id=self._device_id
        )

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
        else:
            raise Exception("The device_id already exists {}".format(device_id))

    def set_capacity(self, device_id, capacity):
        """set the capacity for a power source"""
        d = self.get(device_id)
        # if d.load <= capacity:
        d.set_capacity(capacity)
        # else:
            # raise Exception(
                # "Attempt to set the capacity for a power source that is less than the load ({} > {})".format(d.load, capacity)
            # )

    def set_price(self, device_id, price):
        """set the price of electricity for a power source"""
        d = self.get(device_id)
        d.price = price

    def set_load(self, device_id, load):
        """set the load for a specific power source"""
        d = self.get(device_id)
        if not d.is_available():
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
        return sum(d.capacity for d in self.power_sources if d.is_available())

    def total_load(self):
        """calculate the total load on all the power sources"""
        return sum(d.load for d in self.power_sources)

    def can_handle_load(self, new_load):
        """Is there enough capacity to handle the load?"""
        return (self.total_load() + new_load) <= self.total_capacity()

    def has_available_power_sources(self):
        """Are there powersources configured and available for use?"""
        return True if len([p for p in self.power_sources if p.is_available()]) else False

    def add_load(self, new_load):
        """"""
        # exit immediately if adding no load
        if new_load == 0:
            return True

        success = False
        # check if there is enough capacity between all devices to handle the load
        # if removing power then always ok
        if new_load < 0 or self.can_handle_load(new_load):
            # there is capacity available to handle the load
            power_sources = self.get_available_power_sources()
            if new_load > 0:
                # if adding power then sort by the cheapest price
                power_sources.sort(lambda a, b: cmp(a.price, b.price))
            else:
                # if removing power then sort by the highest price
                # remove load from the most expensive first
                power_sources.sort(lambda a, b: cmp(b.price, a.price))

            for power_source in power_sources:
                # get the power available
                available = power_source.capacity - power_source.load
                if available < new_load:
                    # requesting to add more power than is available
                    # split up between power sources
                    power_source.add_load(available)
                    new_load -= available
                else:
                    power_source.add_load(new_load)
                    new_load = 0
                    success=True
                    break
        return success

    def remove_load(self, new_load):
        """Remove load from the system"""
        # exit immediately if adding no load
        if new_load == 0:
            return True
        elif new_load > 0:
            return self.add_load(new_load)
        elif abs(new_load) > self.total_load():
            # trying to remove more load than is actually there
            raise Exception("Trying to remove more load than is on the system.")

        success = False
        # check if there is enough capacity between all devices to handle the load
        # if removing power then always ok
        # there is capacity available to handle the load
        power_sources = self.get_available_power_sources()
        # if removing power then sort by the highest price
        # remove load from the most expensive first
        power_sources.sort(lambda a, b: cmp(b.price, a.price))

        for power_source in [p for p in power_sources if p.load > 0]:
            # get the power available
            available = power_source.capacity - power_source.load
            if abs(new_load) > power_source.load:
                # removing more load than is on this power source
                new_load += power_source.load
                power_source.set_load(0.0)
            else:
                power_source.add_load(new_load)
                new_load = 0
                success=True
                break
        return success


    def optimize_load(self):
        """
        Check that the loads are optimally distributed among the power sources.
        Move load from the more expensive power sources to the cheaper ones.
        """
        remaining_load = self.total_load()
        starting_load = remaining_load
        if remaining_load == 0:
            # no need to do anything if there's no load
            return

        # power_sources = self.get_available_power_sources()
        # # sort by the cheapest price
        # power_sources.sort(lambda a, b: cmp(a.price, b.price))
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
                        ps.set_load(0.0)
                else:
                    if remaining_load > ps.capacity:
                        # can't put all the remaining load on this power source
                        # set to 100% and try the next power source
                        if ps.load != ps.capacity:
                            ps.set_load(ps.capacity)
                        remaining_load -= ps.capacity
                    else:
                        # this power source can handle all of the remaining load
                        if ps.load != remaining_load:
                            ps.set_load(remaining_load)
                        remaining_load = 0

        if remaining_load != 0:
            raise Exception ("Error optimizing the load.")
        elif starting_load != self.total_load():
            raise Exception("starting/ending loads do not match {} != {}".format(starting_load, self.total_load()))

    def get_available_power_sources(self):
        """get the power sources that have a non-zero capacity"""
        return filter(lambda d: d.is_available(), self.power_sources)

    def get_changed_power_sources(self):
        """return a list of powersources that have been changed"""
        return [p for p in self.power_sources if p.load_changed]

    def reset_changed(self):
        """Reset all the changed flags on all power sources"""
        [p.reset_changed() for p in self.power_sources]

