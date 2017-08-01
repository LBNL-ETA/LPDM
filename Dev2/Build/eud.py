
########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""
    Implementation of a general EUD device, which requests and consumes certain amounts of power.
    For current simplicity, the EUD maintains up to one connection with a grid controller at a time
    and is connected to no other devices. Hence, its only messaging occurs with the Grid Controller
    it is connected to.
"""

from Build.device import Device
from Build.message import Message
from abc import abstractmethod


class Eud(Device):

    def __init__(self, device_id, device_type, supervisor, time=0, read_delay=.001):
        # call the super constructor
        super().__init__(device_id, device_type, supervisor, time, read_delay)
        self._allocated = {}  # Dictionary of devices and how much the device has been allocated by those devices.
                              # NOTE: All values must be negative (EUD's cannot send power as of now).

    ##
    # When the device receive See Device Superclass Description

    @abstractmethod 
    def process_power_message(self, sender_id, new_power):
        pass  # TODO: Or should this be EUD generalized?

    @abstractmethod 
    def process_price_message(self, sender_id, new_price):
        pass

    @abstractmethod
    def process_request_message(self, sender, request_amt):
        pass

    @abstractmethod
    def process_allocate_message(self, sender, allocate_amt):
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

    # @param device_id the id of the device which has allocated the amount of power
    # @param allocate_amt the amount of power allocated by that device. Must be positive. Device will store this as a
    # NEGATIVE value to indicate that it is receiving power.
    #
    def set_allocated(self, device_id, allocate_amt):
        if allocate_amt < 0:
            raise ValueError("EUD cannot allocate to provide power")
        else:
            self._allocated[device_id] = -allocate_amt  # negative because it is receiving.



    ##
    # Method to be called once it needs to recalculate
    #

    @abstractmethod
    def modulate_consumption(self):
        pass

    ##
    # TODO: THIS
    # call this function to send a new messg

    def send_request(self, target_id, request_amt):
        if request_amt > 0:
            raise ValueError("EUD cannot request to distribute power")
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, ))
