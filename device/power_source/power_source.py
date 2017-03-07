

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
    Base class for power sources (diesel generator, battery, pv, ...)
"""
from device.device import Device
from abc import ABCMeta, abstractmethod

class PowerSource(Device):
    def __init__(self, config = {}):
        # call the super constructor
        Device.__init__(self, config)

        # define a capacity property
        self._capacity = config.get("capacity", None)
        self._current_fuel_price = config.get("current_fuel_price", None)

    # def init(self):
        # """Run any initialization functions for the device"""
        # # setup the events at time=0 to let the grid controller know about
        # # the device's price and capacity
        # self.set_initial_price_event()
        # self.set_initial_capacity_event()
        # self.process_events()

    # def process_events(self):
        # "Process any events that need to be processed"
        # remove_items = []
        # for event in self._events:
            # if event["time"] <= self._time:
                # if event["operation"] == "emit_initial_price":
                    # self.broadcast_new_price(self._current_fuel_price, target_device_id=self._grid_controller_id),
                    # remove_items.append(event)
                # elif event["operation"] == "emit_initial_capacity":
                    # self.broadcast_new_capacity(self._capacity, target_device_id=self._grid_controller_id)
                    # remove_items.append(event)

        # # remove the processed events from the list
        # if len(remove_items):
            # for event in remove_items:
                # self._events.remove(event)

    @abstractmethod
    def on_power_change(self, source_device_id, target_device_id, time, power):
        """The GC calls this method to tell the power source how much power to output"""
        pass

    @abstractmethod
    def on_time_change(self, new_time):
        """A time change has occured"""
        pass

    # def set_initial_price_event(self):
        # """Let the grid controller know of the initial price of energy"""
        # self._events.append({"time": 0, "operation": "emit_initial_price"})

    # def set_initial_capacity_event(self):
        # """Let the grid controller know of the initial capacity of the device"""
        # self._events.append({"time": 0, "operation": "emit_initial_capacity"})

