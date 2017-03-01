

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
from device.device import Device
import logging
import pprint

class Pv(Device):
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
        self._device_type = "pv"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "pv"

        self._current_power_output = 0
        self._pv_file_name = "pv_data.csv"
        self._power_profile = None

        # call the super constructor
        Device.__init__(self, config)

        self.loadPowerProfile()

    def onPowerChange(self, time, new_power):
        "Receives messages when a power change has occured"
        return

    def onPriceChange(self, new_price):
        "Receives message when a price change has occured"
        return

    def calculateNextTTIE(self):
        return

    def loadPowerProfile(self):
        "Load the power profile for each 15-minute period of the day"

        print "real path = {}".format(os.path.dirname(os.path.realpath(__file__)))
        self._power_profile = []
        for line in open(os.path.join(os.path.dirname(os.path.realpath(__file__)), self._pv_file_name)):
            parts = line.strip().split(',')
            time_parts = parts[0].split(':')
            time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
            self._power_profile.append({"time": time_secs, "power": float(parts[1])})

        self.logMessage("Power profile loaded: {}".format(pprint.pformat(self._power_profile)))

    def setPowerOutput(self, time, value):
        self._time = time
        self._current_power_output = value
        self.logMessage("Update power output {}".format(value))

    def getMaximumPower(self, time):
        self._time = time
        time_of_day = self.timeOfDaySeconds()
        found_time = None
        for item in self._power_profile:
            found_time = item
            if time_of_day < item["time"]:
                break

        if found_time:
            return found_time["power"]
        else:
            raise Exception("An error occured getting the pv power output")


