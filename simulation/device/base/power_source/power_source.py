

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
from device.base.device import Device
from abc import ABCMeta, abstractmethod
import logging

class PowerSource(Device):
    def __init__(self, config = {}):
        # call the super constructor
        Device.__init__(self, config)

        self._capacity = config.get("capacity", None)
        self._current_capacity = 0.0

        self._current_fuel_price = config.get("current_fuel_price", None)
        self._events = []

    @abstractmethod
    def on_power_change(self, source_device_id, target_device_id, time, power):
        """The GC calls this method to tell the power source how much power to output"""
        pass

    @abstractmethod
    def on_time_change(self, new_time):
        """A time change has occured"""
        pass

    def make_available(self):
        """Make the power source available, ie set its capacity to a non-zero value"""
        self._current_capacity = self._capacity
        self.broadcast_new_capacity()

    def make_unavailable(self):
        """Make the power source unavailable, ie set its capacity to zero"""
        self._current_capacity = 0.0
        self.broadcast_new_capacity()

    def is_available(self):
        """Is the current powersource available? ie current capacity > 0"""
        return self._current_capacity > 0
