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
from Build.event import Event
from Build.message import Message, MessageType


class UtilityMeter(Device):

    def __init__(self, device_id, supervisor, connected_devices=None):
        super().__init__(device_id, "Utility Meter", supervisor, connected_devices=connected_devices)
        self._loads = {}  # dictionary of devices and loads to those devices.
        self._price = 0

    # Turn the utility meter on.
    # TODO: Rename this function to make more clear after running Mike simulations
    def on(self):
        self._logger.info(self.build_message("Turning on utility meter", "turn_on", 1))

    ##
    # Sets the price of the utility meter.
    # @param price the new price to set it to.
    #
    def set_price(self, price):
        self._price = price

    ##
    # Adds a price schedule for this utility
    # @oaram price_schedule a list of price, hour tuples that the utility sets its price at
    #
    def setup_price_schedule(self, price_schedule):
        for price, hour in price_schedule:
            price_event = Event(self.set_price, price)
            time_sec = hour * 3600
            self.add_event(price_event, time_sec)



    # __________________________________ Messaging Functions _______________________ #

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self._loads[sender_id] = new_power
        self.recalc_sum_power(prev_power, new_power)

    ##
    # Method to be called when device receives a price message
    #
    # @param new_price the new price value

    def process_price_message(self, sender_id, new_price):
        pass  # utility does not change its price based on prices of devices.

    ##
    # Method to be called when device receives a request message, indicating a device is requesting to
    # either provide or receive the requested quantity of power.
    #
    # @param request_amt the amount the sender is requesting to provide (positive) or to receive (negative).
    def process_request_message(self, sender_id, request_amt):
        """provide the sender exactly what they request"""
        self._loads[sender_id] = -request_amt
        self.send_power_message(sender_id, -request_amt)

    ##
    # Utility Meter does not process allocate messages.

    def process_allocate_message(self, sender_id, allocate_amt):
        pass

    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This Utility Meter is connected to no such device")
        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))


    ##
    # TODO: Give the device an average price statistic to calculate.
    #
    def device_specific_calcs(self):
        """
        self._logger.info(self.build_message(
            message="average price sold energy",
            tag="average sell price",
            value=self._battery.sum_charge_wh
        ))

        self._logger.info(self.build_message(
            message="average price purchased energy",
            tag="battery sum discharge wh",
            value=self._battery.sum_charge_wh
        ))
        """
        pass