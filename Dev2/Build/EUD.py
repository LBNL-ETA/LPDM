
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
    Implementation of a general EUD device, which requests and consumes cerain amounts of power. 
"""

from Build import Device
from abc import abstractmethod


class Eud(Device):
    def __init__(self, device_id, supervisor):
        # call the super constructor
        super().__init__(self, device_id, supervisor)
        self.allocated = 0 

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

    """
    Once a grid controller has sent an allocate message, the EUD stores the value allocated in a field. 
    The EUD can consume any amount of power up to the allocate received quantity. 

    """

    def set_allocated(self, allocate):
        self.allocated = allocate

    def send_request(self, request):
        pass
