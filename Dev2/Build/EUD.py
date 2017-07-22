
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
    Implementation of a general EUD device, which requests and consumes certain amounts of power.
    For current simplicity, the EUD maintains up to one connection with a grid controller at a time
    and is connected to no other devices. Hence, its only messaging occurs with the Grid Controller
    it is connected to.
"""

from Build import Device
from abc import abstractmethod


class Eud(Device):
    def __init__(self, device_id, supervisor):
        # call the super constructor
        super().__init__(self, device_id, supervisor)
        self._allocated = 0

    ##
    # When the device receive See Device Superclass Description

    @abstractmethod 
    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        pass

    @abstractmethod 
    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        pass

    @abstractmethod
    def on_request(self, target, request_amt):
        pass

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power.
    #
    # @param allocated_amt the amount allocated to provide to another device (positive) or to receive from another
    # device (negative).
    def on_allocate(self, allocate_amt):
        self.set_allocated(allocate_amt)
        self.modulate_consumption()
        #TODO: self.on_power_change()?

    """
    Once a grid controller has sent an allocate message, the EUD stores the value allocated in a field. 
    The EUD can consume any amount of power up to the allocate received quantity. 

    """
    ##
    # This method is called once the EUD receives a message from its controller that has allocated
    # to provide a certain amount of power (the EUD should never receive a negative allocate message
    # from the grid controller since it is only a power consumer, not provider).
    #
    def set_allocated(self, allocate):
        self._allocated = allocate

    ##


    #
    @abstractmethod
    def modulate_consumption(self):
        pass


    def send_request(self, request):
        pass
