

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
    Implementation of a battery
"""

from device.power_source import PowerSource
import logging

class Battery(PowerSource):
    """
        Device implementation of a battery.

        The battery is fully controlled by the grid controller, so there's no TTIE calculations;
        and it doesn't respond to any power, price, or time changes.

        Methods:
            start_charging: starts the battery charging,
            stop_charging: stops the battery charging,
            state_of_charge: gets the current SOC of the battery
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the grid controller

                keys:
                    "device_name" (string): Name of the device
                    "capacity" (float): Capacity of the battery (kWh)
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the battery wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the battery wants to stop charging
                    "max_charge_rate" (float): Max charge rate (Watts)
                    "roundtrip_eff" (float): Fraction of power that is stored and available for withdrawl
        """
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "battery"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "battery"
        self._capacity = float(config["capacity"]) if type(config) is dict and "capacity" in config.keys() else 5.0
        self._current_soc = float(config["current_soc"]) if type(config) is dict and "current_soc" in config.keys() else 1.0
        self._min_soc = float(config["min_soc"]) if type(config) is dict and "min_soc" in config.keys() else 0.2
        self._max_soc = float(config["max_soc"]) if type(config) is dict and "max_soc" in config.keys() else 0.8
        self._max_charge_rate = float(config["max_charge_rate"]) if type(config) is dict and "max_charge_rate" in config.keys() else 1000.0
        self._roundtrip_eff = float(config["roundtrip_eff"]) if type(config) is dict and "roundtrip_eff" in config.keys() else 0.9
        self._min_soc_refresh_rate = 60
        self._battery_on_time = None
        self._last_update_time = None
        self._charge_start_time = None
        self._is_charging = False
        self._is_discharging = False

    def init(self):
        """no need to do any initialization for the battery"""
        pass

    def capacity(self):
        "Return the capcity of the battery (W)"
        return self._capacity * 1000.0

    def on_power_change(self, time, new_power):
        "Receives messages when a power change has occured"
        return

    def on_price_change(self, new_price):
        "Receives message when a price change has occured"
        return

    def calculate_next_ttie(self):
        return

    def max_charge_rate(self):
        return self._max_charge_rate

    def charge_rate(self):
        "Charge rate (W)"
        return self._max_charge_rate * self._roundtrip_eff

    def start_charging(self, time):
        self._time = time
        if not self._is_charging:
            self.log_message("Start charging battery (soc = {})".format(self._current_soc))
            self._is_charging = True
            self._last_update_time = time
        return

    def stop_charging(self, time):
        self._time = time
        if self._is_charging:
            self.log_message("Stop charging battery (soc = {})".format(self._current_soc))
            self._is_charging = False
            self._last_update_time = time
        return

    def is_charging(self):
        return self._is_charging

    def wants_to_stop_charging(self):
        return self._current_soc >= self._max_soc

    def wants_to_start_charging(self):
        return self._current_soc <= self._min_soc

    def discharge(self, amount):
        "Remove energy (kwh) from the battery when requested, battery must be set to discharge first"
        if self._is_discharging:
            self._current_soc = ((self._capacity * self._current_soc) - amount) / self._capacity
        else:
            raise Exception("Battery must have been set to discharge before removing energy.")
        return

    def start_discharging(self, time):
        self._time = time
        if not self._is_charging and not self._is_discharging:
            self.log_message("Start discharging battery (soc = {})".format(self._current_soc))
            self._is_discharging = True
            self._last_update_time = time

    def stop_discharging(self, time):
        self._time = time
        if self._is_discharging:
            self.log_message("Stop discharging battery (soc = {})".format(self._current_soc))
            self._is_discharging = False
            self._last_update_time = time

    def is_discharging(self):
        return self._is_discharging

    def state_of_charge(self):
        "Returns the current SOC"
        return self._current_soc

    def update_state_of_charge(self, time, load_on_battery):
        self._time = time
        if not self._last_update_time or time - self._last_update_time > self._min_soc_refresh_rate:
            if self._is_charging:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) + (self.charge_rate() * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)
            elif self._is_discharging and load_on_battery:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) - (load_on_battery * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)

            self._last_update_time = time

