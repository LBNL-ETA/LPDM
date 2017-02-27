

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
    Implementation of a generic temperature dependend device
"""

from device import Device
import logging
import colors
import pprint

class TemperatureDependentDevice(Device):
    """
    """

    def __init__(self, config):
        """
        """
        self._device_type = config["device_type"] if type(config) is dict and "device_type" in config.keys() else "temp_dep_device"
        if not "_device_type" in dir(self):
            self._device_type = "temp_dep_device"

        if not "_device_name" in dir(self):
            self._device_name = "temp_dep_device"

        self._current_outdoor_temperature = None

        # update the temperature every hour
        self._temperature_update_interval = 60.0 * 60.0

        if not "_events" in dir(self):
            self._events = []

        # call the super constructor
        Device.__init__(self, config)

        # build an hourly temperature profile
        self._temperature_hourly_profile = self.buildHourlyTemperatureProfile()
        self.logMessage("Hourly temperature profile: \n{}".format(pprint.pformat(self._temperature_hourly_profile, indent=4)))
        self.scheduleNextEvents()

    def buildHourlyTemperatureProfile(self):
        """
        these are average hourly tempeartures for edwards airforce base from august 2015
        """
        return [
            {"hour": 0, "hour_seconds": 3600.0 * 0, "value": 73.7},
            {"hour": 1, "hour_seconds": 3600.0 * 1, "value": 72.2},
            {"hour": 2, "hour_seconds": 3600.0 * 2, "value": 70.8},
            {"hour": 3, "hour_seconds": 3600.0 * 3, "value": 69.6},
            {"hour": 4, "hour_seconds": 3600.0 * 4, "value": 68.1},
            {"hour": 5, "hour_seconds": 3600.0 * 5, "value": 68.6},
            {"hour": 6, "hour_seconds": 3600.0 * 6, "value": 74.0},
            {"hour": 7, "hour_seconds": 3600.0 * 7, "value": 79.6},
            {"hour": 8, "hour_seconds": 3600.0 * 8, "value": 85.6},
            {"hour": 9, "hour_seconds": 3600.0 * 9, "value": 90.0},
            {"hour": 10, "hour_seconds": 3600.0 * 10, "value": 93.8},
            {"hour": 11, "hour_seconds": 3600.0 * 11, "value": 96.5},
            {"hour": 12, "hour_seconds": 3600.0 * 12, "value": 98.6},
            {"hour": 13, "hour_seconds": 3600.0 * 13, "value": 99.6},
            {"hour": 14, "hour_seconds": 3600.0 * 14, "value": 99.6},
            {"hour": 15, "hour_seconds": 3600.0 * 15, "value": 99.0},
            {"hour": 16, "hour_seconds": 3600.0 * 16, "value": 96.7},
            {"hour": 17, "hour_seconds": 3600.0 * 17, "value": 92.3},
            {"hour": 18, "hour_seconds": 3600.0 * 18, "value": 87.9},
            {"hour": 19, "hour_seconds": 3600.0 * 19, "value": 83.8},
            {"hour": 20, "hour_seconds": 3600.0 * 20, "value": 80.9},
            {"hour": 21, "hour_seconds": 3600.0 * 21, "value": 78.3},
            {"hour": 22, "hour_seconds": 3600.0 * 22, "value": 76.4},
            {"hour": 23, "hour_seconds": 3600.0 * 23, "value": 74.6}
        ]

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        return

    def onTimeChange(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time

        self.processEvents()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def processEvents(self):
        "Process any events that need to be processed"

        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "update_temperature":
                    self.processTemperatureChange()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return

    def scheduleNextEvents(self):
        """schedule the next temperature update (in one hour)"""
        # first search for existing events
        search_events = [event for event in self._events if event["operation"] == "update_temperature"]
        if not len(search_events):
            self._events.append({"time": self._time + self._temperature_update_interval, "operation": "update_temperature"})

    def processTemperatureChange(self):
        """Update the current outdoor temperature"""
        # get the time of day in seconds
        time_of_day = self.timeOfDaySeconds()
        found_temp = None
        for temp in self._temperature_hourly_profile:
            if temp["hour_seconds"] >= time_of_day:
                found_temp = temp
                break

        if found_temp:
            self.updateTemperature(temp["value"])

    def updateTemperature(self, new_temperature):
        "This method needs to be implemented by a device if it needs to act on a change in temperature"
        self._current_outdoor_temperature = new_temperature
        self.logMessage("Outdoor temperature changed to {}".format(new_temperature))
        return

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcastNewTTIE(ttie)
