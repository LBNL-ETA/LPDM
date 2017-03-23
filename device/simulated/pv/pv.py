

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
"""

import os
from device.base.power_source import PowerSource
import pprint

class Pv(PowerSource):
    """
        Device implementation of a PV module.

        The pv is fully controlled by the grid controller, so there's no TTIE calculations;
        and it doesn't respond to any power, price, or time changes.

        Methods:
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values

                keys:
                    "device_name" (string): Name of the device
                    "capacity" (float): Capacity of the battery (kWh)
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the battery wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the battery wants to stop charging
                    "max_charge_rate" (float): Max charge rate (Watts)
                    "roundtrip_eff" (float): Fraction of power that is stored and available for withdrawl
                    "battery_on_time" (int): Time (seconds) when the battery was turned on
        """
        # call the super constructor
        PowerSource.__init__(self, config)

        self._device_type = "pv"
        self._device_name = config.get("device_name", "pv")
        self._pv_file_name = config.get("pv_file_name", "pv_data.csv")
        self._capacity_update_interval = config.get("capacity_update_interval", 15.0 * 60.0)
        self._price = 0.0

        self._power_profile = None

    def init(self):
        """Load the power profile for the pv on initialization"""
        self.load_power_profile()
        self.make_available()
        self.set_update_capacity_event()
        self.broadcast_new_price(self._price, target_device_id=self._grid_controller_id)
        self.calculate_next_ttie()

    def make_available(self):
        """Make the power source available, ie set its capacity to a non-zero value"""
        self.set_capacity()
        self.broadcast_new_capacity()

    def set_update_capacity_event(self):
        """Set the next event for updating the pv capacity"""
        self._events.append({"time": self._time + self._capacity_update_interval, "operation": "update_capacity"})

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self.process_events()
        self.calculate_next_ttie()

    def process_events(self):
        "Process any events that need to be processed"
        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "update_capacity":
                    self.set_capacity()
                    self.set_update_capacity_event()
                    remove_items.append(event)

        # remove the processed events from the list
        if len(remove_items):
            for event in remove_items:
                self._events.remove(event)

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        self._power_level = new_power
        self._logger.debug(
            self.build_message(
                message="Update power output {}".format(new_power),
                tag="power",
                value=self._power_level
            )
        )
        return

    def on_price_change(self, new_price):
        "Receives message when a price change has occured"
        return

    def load_power_profile(self):
        "Load the power profile for each 15-minute period of the day"

        self._power_profile = []
        for line in open(os.path.join(os.path.dirname(os.path.realpath(__file__)), self._pv_file_name)):
            parts = line.strip().split(',')
            time_parts = parts[0].split(':')
            time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
            self._power_profile.append({"time": time_secs, "power": float(parts[1])})

    def set_capacity(self):
        """set the capacity of the pv at the current time"""
        time_of_day_secs = self.time_of_day_seconds()
        found_time = None
        for item in self._power_profile:
            if  item["time"] > time_of_day_secs:
                break
            found_time = item

        if found_time:
            self._current_capacity = found_time["power"]
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
            return found_time["power"]
        else:
            raise Exception("An error occured getting the pv power output")
