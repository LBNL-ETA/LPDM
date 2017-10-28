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

from Build.device import Device, SECONDS_IN_DAY
from Build.event import Event
from Build.message import Message, MessageType


class UtilityMeter(Device):

    def __init__(self, device_id, supervisor, msg_latency=0, schedule=None, runtime=SECONDS_IN_DAY, multiday=0,
                 price_schedule=None, price_multiday=0, connected_devices=None):
        super().__init__(device_id, "Utility Meter", supervisor, msg_latency=msg_latency, schedule=schedule,
                         connected_devices=connected_devices, total_runtime=runtime, multiday=multiday)
        self._loads = {}  # dictionary of devices and loads to those devices.
        self._sell_price = 0
        self._buy_price = 0
        if price_schedule:
            self.setup_price_schedule(price_schedule, multiday=price_multiday, runtime=runtime)

    # Turn the utility meter on.
    def turn_on(self):
        self._logger.info(self.build_log_notation("Turning on utility meter", "turn_on", 1))

    def set_prices(self, sell_price=None, buy_price=None):
        if sell_price:
            self._sell_price = sell_price
            self._logger.info(self.build_log_notation("set sell price", "set sell price", sell_price))
        if buy_price:
            self._buy_price = buy_price
            self._logger.info(self.build_log_notation("set buy price", "set buy price", buy_price))
        self.broadcast_price_levels(self._sell_price, self._buy_price)

    ##
    # Adds a price schedule for this utility
    # @oaram price_schedule a list of hour, sell_price, buy_price tuples that the utility sets its price at
    # @param multiday how many days of the scheduling to set as a repeating
    #
    def setup_price_schedule(self, price_schedule, multiday=0, runtime=SECONDS_IN_DAY):
        curr_day = 0
        if multiday:
            while curr_day < runtime:
                for hour, sell_price, buy_price in price_schedule:
                    if hour > (multiday * 24):
                        break
                    price_event = Event(self.set_prices, sell_price, buy_price)
                    time_sec = (int(hour) * 3600) + curr_day
                    self.add_event(price_event, time_sec)
                curr_day += multiday * SECONDS_IN_DAY
        else:
            for hour, sell_price, buy_price in price_schedule:
                price_event = Event(self.set_prices, sell_price, buy_price)
                time_sec = int(hour) * 3600
                self.add_event(price_event, time_sec)

    # __________________________________ Messaging Functions _______________________ #

    ##
    # Process a power message from a grid controller. Always provide what is demanded,
    # assuming less than maximum output capacity.
    # @param new_power the new power from the sender's perspective

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self._loads[sender_id] = -new_power
        self.recalc_sum_power(prev_power, -new_power)

    ##
    # Method to be called when device receives a price message
    #
    # @param new_price the new price value

    def process_price_message(self, sender_id, new_price, extra_info):
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

        self._logger.info(self.build_log_notation(message="power msg to {}".format(target_id),
                                                  tag="power message", value=power_amt))

        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    def send_price_message(self, target_id, sell_price, buy_price):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This Utility Meter is connected to no such device")

        self._logger.info(self.build_log_notation(message="price msg to {}".format(target_id),
                                                  tag="price message", value="{}, {}".format(sell_price, buy_price)))

        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE,
                                       value=sell_price, extra_info=buy_price))

    ##
    # Informs all connected devices of the utility meter's buy price
    # @param price the price to broadcast to all connected devices

    def broadcast_price_levels(self, sell_price, buy_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(device_id, sell_price, buy_price)
    ##
    # TODO: Give the utm an average price statistic to calculate.
    #

    def device_specific_calcs(self):

        """
        self._logger.info(self.build_log_notation(
            message="average price sold energy",
            tag="average sell price",
            value=self._battery.sum_charge_wh
        ))

        self._logger.info(self.build_log_notation(
            message="average price purchased energy",
            tag="battery sum discharge wh",
            value=self._battery.sum_charge_wh
        ))
        """
        pass
