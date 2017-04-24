

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

from device.base.device import Device
from device.scheduler import LpdmEvent
import logging

class FixedConsumption(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "fixed_consumption"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "FixedConsumption")

        # set the units
        self._units = 'W'

    def init(self):
        self.set_initial_event()

    def set_initial_event(self):
        """Setup the initial event to turn on the device at t=0"""
        new_event = LpdmEvent(0.0, "turn_on")
        self._events.append(new_event)
        self.broadcast_new_ttie(new_event.ttie)

    def should_be_in_operation(self):
        """Should always be on"""
        return True

    def process_events(self):
        """Process the ttie event"""
        if len(self._events) > 0:
            for evt in self._events:
                if evt.ttie <= self._time and evt.value == "turn_on":
                    self.turn_on()

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

    def on_capacity_change(self, source_device_id, target_device_id, time, capacity):
        """A device has changed its capacity, check if the eud should be in operation"""
        self._time = time
        if not self._in_operation and self.should_be_in_operation():
            self._logger.debug(
                self.build_message(
                    message="eud should be on",
                    tag="capacity_change_on",
                    value=1
                )
            )
            self.turn_on()

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self._time = time
            if new_price != self._price:
                self._logger.debug(
                    self.build_message(
                        message="new price",
                        tag="receive_price",
                        value=new_price
                    )
                )
                self.set_price(new_price)

    def on_time_change(self, new_time):
        "Receives message when a time change has occured"
        self._time = new_time
        self.process_events()
        pass
