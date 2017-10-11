from Build.device import Device


class PV(Device):
    ################################################################################################################################
    # *** Copyright Notice ***
    #
    # "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0"
    # Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory
    # (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
    #
    # If you have questions about your rights to use or distribute this software, please contact
    # Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
    ################################################################################################################################

    """
    Implementation of a PV module


    Device implementation of a PV module.

    The pv is fully controlled by the grid controller, so there's no TTIE calculations;
    and it doesn't respond to any power, price, or time changes.

    Methods:
    """
    # @param power_profile a list of ratios of power production for different times in the day in format
    # [(seconds, power_ratio), ...]
    # @param peak_power the maximum power output of this device
    def __init__(self, device_id, supervisor, power_profile, peak_power, time=0, msg_latency=0,
                 schedule=None, connected_devices=None):

        super().__init__(device_id=device_id, device_type="pv", supervisor=supervisor,
                         time=time, msg_latency=msg_latency, schedule=schedule, connected_devices=connected_devices)
        self._peak_power = peak_power

    def setup_power_schedule(self, power_profile, peak_power):
        for time, power in power_profile:
            power_event = Event(update_power_status, peak_power)
            self.add_event(power_event, time)



    def process_events(self):
        "Process any events that need to be processed"
        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "update_capacity":
                    self.set_capacity()
                    remove_items.append(event)

        # remove the processed events from the list
        if len(remove_items):
            for event in remove_items:
                self._events.remove(event)

        self.set_update_capacity_event()

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        self.set_power_level(new_power)
        self._logger.debug(
            self.build_message(
                message="Update power output {}".format(new_power),
                tag="power",
                value=self._power_level
            )
        )

    def on_price_change(self, new_price):
        "Receives message when a price change has occured"
        return

    def load_power_profile(self):
        "Load the power profile for each 10-minute period of the day"

        self._power_profile = []
        for raw_line in open(os.path.join(os.path.dirname(os.path.realpath(__file__)), self._pv_file_name)):
            for line in raw_line.split("\r"):
                parts = line.strip().split(',')
                if len(parts) == 2 and parts[0].strip():
                    time_parts = parts[0].split(':')
                    time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
                    self._power_profile.append({"time": time_secs, "production": float(parts[1])})

    def set_capacity(self):
        """set the capacity of the pv at the current time"""
        if self._smap_enabled:
            self.set_capacity_from_smap()
        else:
            self.set_capacity_from_file()

    def set_capacity_from_smap(self):
        """Get the capacity values from smap"""
        if not self._smap_enabled:
            raise Exception("Call to set capacity values from sMAP, but sMAP disabled")
        # get the new capacity value from the smap stream
        uuid, ts, new_capacity = self.download_most_recent_point(
            self._smap["capacity"]["smap_root"],
            self._smap["capacity"]["stream"]
        )

        self._logger.debug(self.build_message(
            message="received capaacity from smap",
            tag="smap_capacity",
            value=new_capacity
        ))
        if self._current_capacity != new_capacity:
            # broadcast new capacity if it has changed
            self._current_capacity = new_capacity
            self.broadcast_new_capacity()
            self._logger.debug(
                self.build_message(
                    message="setting pv capcity to {}".format(self._current_capacity),
                    tag="capacity",
                    value=self._current_capacity
                )
            )

    def set_capacity_from_file(self):
        """Get the capacity values from a file"""
        time_of_day_secs = self.time_of_day_seconds()
        found_time = None
        for item in self._power_profile:
            if item["time"] > time_of_day_secs:
                break
            found_time = item

        if found_time:
            self._current_capacity = found_time["production"] * self._capacity
            self.broadcast_new_capacity()
            self._logger.debug(
                self.build_message(
                    message="setting pv capcity to {}".format(self._current_capacity),
                    tag="capacity",
                    value=self._current_capacity
                )
            )
        else:
            self._logger.error(
                self.build_message("Unable to find capacity value")
            )
            raise Exception("An error occured getting the pv power output")

    def get_maximum_power(self, time):
        self._time = time
        time_of_day = self.time_of_day_seconds()
        found_time = None
        for item in self._power_profile:
            found_time = item
            if time_of_day < item["time"]:
                break

        if found_time:
            return found_time["production"]
        else:
            raise Exception("An error occured getting the pv power output")

            ##

        # All device specific power consumption statistics are added here

    ##
    # PV does not calculate any new information
    def device_specific_calcs(self):
        pass


