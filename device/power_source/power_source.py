

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
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

    @abstractmethod
    def init(self):
        """Run any initialization functions for the device"""
        pass

    @abstractmethod
    def refresh(self):
        """Refresh the device"""
        pass

    @abstractmethod
    def on_power_change(self, source_device_id, target_device_id, time, power):
        """A power change has occured"""
        pass

    @abstractmethod
    def on_time_change(self, new_time):
        """A power change has occured"""
        pass

    @abstractmethod
    def set_initial_price_event(self):
        """Let the grid controller know of the initial price of energy"""
        pass

    @abstractmethod
    def calculate_next_ttie(self):
        """calculate the next ttie"""
        pass
