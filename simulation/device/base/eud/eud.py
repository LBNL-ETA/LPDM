

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
    Implementation of a general EUD device
"""
from abc import ABCMeta, abstractmethod
from device.base.device import Device
import logging

class Eud(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

#abstract methods 
#__________________________________________________________________________________
    @abstractmethod 
    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        pass

    @abstractmethod
    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        pass


    @abstractmethod 
    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        pass


    @abstractmethod
    def on_time_change(self, new_time):
        pass

    @abstractmethod 
    def process_events(self):
        pass

#___________________________________________________________________________________
    
    # eud messaging functions
   

    



