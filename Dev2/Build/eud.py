
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
from Build.message import Message, MessageType
from abc import abstractmethod


class Eud(Device):

    def __init__(self, device_id, device_type, supervisor, time=0, read_delay=.001):
        # call the super constructor
        super().__init__(device_id, device_type, supervisor, time, read_delay)
        self._allocated_in = {}  # Dictionary of devices and how much the device has been allocated by those devices.
                                 # NOTE: All values must be positive, indicating the amount received.
        self._price = 0  # EUD receives price messages from GC's only. For now, assume it will always update price.

    ##
    # Sets the quantity of power that this EUD has been allocated to consume by a specific device

    # @param device_id the id of the device which has allocated the amount of power
    # @param allocate_amt the amount of power allocated by that device. Must be positive.
    #
    def set_allocated(self, device_id, allocate_amt):
        if allocate_amt < 0:
            raise ValueError("EUD cannot allocate to provide power")
        else:
            self._allocated_in[device_id] = allocate_amt

    ##
    # When the device receive See Device Superclass Description

    def process_power_message(self, sender_id, new_power):
        if new_power != self._power_in and new_power > 0:
            self.set_power_in(new_power)
            self.modulate_power()

    def process_request_message(self, sender_id, request_amt):
        # TODO: log this message.
        print("EUD does not process request messages")

    def process_price_message(self, sender_id, new_price):
        self._price = new_price  # EUD always updates its value to the price it receives.
        self.modulate_power()

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power.
    #
    # @param sender_id the device who has allocated to provide the given quantity
    # @param allocated_amt the amount allocated to provide to another device (positive) or to receive from another
    # device (negative).

    def process_allocate_message(self, sender_id, allocate_amt):
        self.set_allocated(sender_id, allocate_amt)
        self.modulate_power()


    ##
    # TODO: THIS
    # call this function to send a new message requesting a given quantity of power from

    def send_request(self, target_id, request_amt):
        if request_amt > 0:
            raise ValueError("EUD cannot request to distribute power")
        if target_id in self._connected_devices.keys() and target_id.startswith("gc"):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    # This method is called when the EUD wishes to inform a grid controller that it is now consuming X watts of power.
    #
    #

    def send_power_message(self, target_id, power_amt):
        if power_amt > 0:
            raise ValueError("EUD cannot distribute power")
        if target_id in self._connected_devices.keys() and target_id.startswith("gc"):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        target_device.receive_message(Message(self._time, self._device_id, MessageType.Power, power_amt))

    ##
    # Method to be called once it needs to recalculate its internal power usage.
    # To be called after price, power level, or allocate has changed.
    # This function will change the EUD's power level, returning the difference of new_power - old_power
    # Must be implemented by all EUD's.

    @abstractmethod
    def modulate_power(self):
        pass