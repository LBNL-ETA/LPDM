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


"""

from Build.device import Device
from Build.message import Message, MessageType


class UtilityMeter(Device):

    def __init__(self, device_id, supervisor, connected_devices=None):
        identifier = "utm{}".format(device_id)
        super().__init__(identifier, "Utility Meter", supervisor, connected_devices)
        self._loads = {} #dictionary of devices and loads to those devices.

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self._loads[sender_id] = new_power
        # TODO: if...

    ##
    # Method to be called when device receives a price message
    #
    # @param new_price the new price value
    #  TODO: This occurs when a device sends a price message. Internal price modulation vs external? Different funcs?

    def process_price_message(self, sender_id, new_price):
        pass  # utility does not change its price based on prices of devices.

    ##
    # Method to be called when device receives a request message, indicating a device is requesting to
    # either provide or receive the requested quantity of power.
    #
    # @param request_amt the amount the device is requesting to provide (positive) or to receive (negative). s
    def process_request_message(self, sender_id, request_amt):
        """provide the sender exactly what they request"""
        self._loads[sender_id] = request_amt
        self.send_power_message(sender_id, request_amt)



    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power. Allocation should only ever occur after request messages
    # have been passed and processed.
    #
    # @param allocated_amt the amount allocated to provide to another device (positive) or to receive from another
    # device (negative). s
    def process_allocate_message(self, sender_id, allocate_amt):
        pass


    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This Utility Meter is connected to no such device")
        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))


