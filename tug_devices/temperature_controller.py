

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
    Implementation of an air conditioner
"""

from device import Device
import logging
import colors
import pprint

class TemperatureController(Device):
    """
    """

    def __init__(self, config):
        """
        """
        self._device_type = "temperature_controller"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "temperature_controller"

        # update the temperature every hour
        self._temperature_update_interval = 60.0 * 60.0

        self._temperature_hourly_profile = self.buildHourlyTemperatureProfile()

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

        self.logMessage("Hourly temperature profile: \n{}".format(pprint.pformat(self._temperature_hourly_profile, indent=4)))
        self.scheduleNextTemperatureUpdate()

    def buildHourlyTemperatureProfile(self):
        """
        these are average hourly tempeartures for edwards airforce base from august 2015
        """
        return [
            {"hour": 0, "hour_seconds": 0, "value": 73.7},
            {"hour": 1, "hour_seconds": 60, "value": 72.2},
            {"hour": 2, "hour_seconds": 60 * 2, "value": 70.8},
            {"hour": 3, "hour_seconds": 60 * 3, "value": 69.6},
            {"hour": 4, "hour_seconds": 60 * 4, "value": 68.1},
            {"hour": 5, "hour_seconds": 60 * 5, "value": 68.6},
            {"hour": 6, "hour_seconds": 60 * 6, "value": 74.0},
            {"hour": 7, "hour_seconds": 60 * 7, "value": 79.6},
            {"hour": 8, "hour_seconds": 60 * 8, "value": 85.6},
            {"hour": 9, "hour_seconds": 60 * 9, "value": 90.0},
            {"hour": 10, "hour_seconds": 60 * 10, "value": 93.8},
            {"hour": 11, "hour_seconds": 60 * 11, "value": 96.5},
            {"hour": 12, "hour_seconds": 60 * 12, "value": 98.6},
            {"hour": 13, "hour_seconds": 60 * 13, "value": 99.6},
            {"hour": 14, "hour_seconds": 60 * 14, "value": 99.6},
            {"hour": 15, "hour_seconds": 60 * 15, "value": 99.0},
            {"hour": 16, "hour_seconds": 60 * 16, "value": 96.7},
            {"hour": 17, "hour_seconds": 60 * 17, "value": 92.3},
            {"hour": 18, "hour_seconds": 60 * 18, "value": 87.9},
            {"hour": 19, "hour_seconds": 60 * 19, "value": 83.8},
            {"hour": 20, "hour_seconds": 60 * 20, "value": 80.9},
            {"hour": 21, "hour_seconds": 60 * 21, "value": 78.3},
            {"hour": 22, "hour_seconds": 60 * 22, "value": 76.4},
            {"hour": 23, "hour_seconds": 60 * 23, "value": 74.6}
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
        # self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def processEvents(self):
        "Process any events that need to be processed"

        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "update_temperature":
                    self.updateTemperature()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return


    # def setNextBatteryUpdateEvent(self):
        # "If the battery is on update its state of charge every X number of seconds"
        # self._events.append({"time": self._time + self._check_battery_soc_rate, "operation": "battery_status"})

    def scheduleNextTemperatureUpdate(self):
        """schedule the next temperature update (in one hour)"""
        # first search for existing events
        search_events = [event for event in self._events if event["operation"] == "update_temperature"]
        if not len(search_events):
            self._events.append({"time": self._time + self._temperature_update_interval, "operation": "update_temperature"})
            self.logMessage("scheduled temperature change for {}".format(self._time + self._temperature_update_interval))

    # def scheduleNextEvents(self):
        # "Schedule upcoming events if necessary"
        # search_events = [event for event in self._events if event["operation"] == "update_temperature"]
        # if not len(search_events):
            # self.setNextBatteryUpdateEvent()
        # return
    def updateTemperature(self):
        """Update the current outdoor temperature"""
        # get the time of day in seconds
        time_of_day = self.timeOfDaySeconds()
        found_temp = None
        for temp in self._temperature_hourly_profile:
            if temp["hour_seconds"] >= time_of_day:
                found_temp = temp
                break

        if found_temp:
            self.current_temperature = temp["value"]
            self.broadcastNewTemperature()

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcastNewTTIE(ttie)

