

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

from device.device import Device
import logging

class FixedConsumption(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "fixed_consumption"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "FixedConsumption")

        # _schedule_array is the raw schedule passed in
        # _dail_y_schedule is the parsed schedule used by the device to schedule events
        self._schedule_array = config["schedule"] if type(config) is dict and config.has_key("schedule") else None
        self._daily_schedule = self.parse_schedule(self._schedule_array) if self._schedule_array else None

        self._power_level = config.get("power_output", 0.0)
        self._events = []

        # set the units
        self._units = 'W'

    def init(self):
        self.set_initial_event()

    def set_initial_event(self):
        """Setup the initial event to turn on the device at t=0"""
        self._events.append({"time": 0.0, "operation": "turn_on"})
        self.broadcast_new_ttie(0.0)

    def process_events(self):
        """Process the ttie event"""
        if len(self._events) > 0:
            for evt in self._events:
                if evt["time"] == self._time and evt["operation"] == "turn_on":
                    if self._power_level > 0:
                        self.turn_on()
                        self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)
                    else:
                        self._logger.error(
                            self.build_message(message="Power output not set for fixed consumption device.")
                        )

    def status(self):
        return {
            "type": self._device_type,
            "name": self._device_name,
            "in_operation": self._in_operation,
            "power_level": self._power_level
        }

    def refresh(self):
        """refresh"""
        pass

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turn_off()

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        pass

    def on_time_change(self, new_time):
        "Receives message when a time change has occured"
        self._time = new_time
        self.process_events()
        pass

    def turn_on(self):
        "Turn on the device"
        if not self._in_operation and self._power_level > 0:
            self._in_operation = True
            self._logger.info(
                self.build_message(
                    message="turn on",
                    tag="on/off",
                    value=1
                )
            )

    def turn_off(self):
        "Turn off the device"

        if self._in_operation:
            self._power_level = 0.0
            self._in_operation = False
            self._logger.info(
                self.build_message(
                    message="turn off eud",
                    tag="on/off",
                    value=0
                )
            )
            self._logger.info(
                self.build_message(
                    message="Power level {}".format(self._power_level),
                    tag="power",
                    value=self._power_level
                )
            )

