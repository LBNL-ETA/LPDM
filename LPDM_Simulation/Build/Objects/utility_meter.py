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
An implementation of the utility meter class. The Utility Meter is a grid entity which can both buy and sell power from
the grid at a predetermined schedule of prices (unlike all other grid equipment entities, its buying price can be
different than its sell price). The utility meter is a 'dumb' entity in the sense that it does no load optimization,
nor does it try to modify or optimize its own state, it simply acts as an unlimited external power buyer and supplier.
"""

from Build.Simulation_Operation.message import Message, MessageType

from Build.Objects.device import Device, SECONDS_IN_DAY
from Build.Simulation_Operation.event import Event


class UtilityMeter(Device):

    def __init__(self, device_id, supervisor, msg_latency=0, schedule=None, runtime=SECONDS_IN_DAY, multiday=0,
                 sell_price_schedule=None, sell_price_multiday=0, buy_price_schedule=None,
                 buy_price_multiday=0, connected_devices=None):

        super().__init__(device_id, "Utility Meter", supervisor, msg_latency=msg_latency, schedule=schedule,
                         connected_devices=connected_devices, total_runtime=runtime, multiday=multiday)
        self._loads = {}  # dictionary of devices and loads to those devices.
        self._sell_price = 0
        self._buy_price = 0
        self._in_operation = False
        self.setup_price_schedules(sell_price_schedule=sell_price_schedule, sell_price_multiday=sell_price_multiday,
                                   buy_price_schedule=buy_price_schedule, buy_price_multiday=buy_price_multiday,
                                   runtime=runtime)

    ##
    # Turn the utility meter on so that it can provide and receive power.
    def turn_on(self):
        self._in_operation = True
        self._logger.info(self.build_log_notation("Turning on utility meter", "turn_on", 1))

    ##
    # Turn the utility meter off so that it can no longer provide and receive power.
    def turn_off(self):
        self._in_operation = False
        self._logger.info(self.build_log_notation("Turning off utility meter", "turn_off", 0))

    ##
    # Change the sell price for this utility meter
    # @param sell_price the sell price to set the value to
    def set_sell_price(self, sell_price):
        prev_sell_price = self._sell_price
        self._sell_price = sell_price
        self._logger.info(self.build_log_notation("set sell price", "set sell price", sell_price))
        if self._sell_price != prev_sell_price:
            self.broadcast_price_levels(sell_price=self._sell_price, buy_price=self._buy_price)

    ##
    # Sets the buy price for this utility meter
    # @param buy_price the buy price to set the value to
    def set_buy_price(self, buy_price):
        prev_buy_price = self._buy_price
        self._buy_price = buy_price
        self._logger.info(self.build_log_notation("set buy price", "set buy price", buy_price))
        if self._buy_price != prev_buy_price:
            self.broadcast_price_levels(sell_price=self._sell_price, buy_price=self._buy_price)

    ##
    # Adds a price schedule for this utility
    # @oaram sell_price_schedule the list of hour, sell_price tuples in
    # @param multiday how many days of the scheduling to set as a repeating
    #
    def setup_price_schedules(self, sell_price_schedule, buy_price_schedule, sell_price_multiday=0,
                              buy_price_multiday=0, runtime=SECONDS_IN_DAY):

        #  Setup sell price schedule events
        if sell_price_schedule:
            curr_day = 0
            if sell_price_multiday:
                while curr_day < runtime:
                    for hour, sell_price in sell_price_schedule:
                        if hour > (sell_price_multiday * 24):
                            break
                        price_event = Event(self.set_sell_price, sell_price)
                        time_sec = (int(hour) * 3600) + curr_day
                        self.add_event(price_event, time_sec)
                    curr_day += sell_price_multiday * SECONDS_IN_DAY
            else:
                for hour, sell_price in sell_price_schedule:
                    price_event = Event(self.set_sell_price, sell_price)
                    time_sec = int(hour) * 3600
                    self.add_event(price_event, time_sec)

        # Set up buy price schedule events
        if buy_price_schedule:
            curr_day = 0
            if buy_price_multiday:
                while curr_day < runtime:
                    for hour, buy_price in buy_price_schedule:
                        if hour > (buy_price_multiday * 24):
                            break
                        price_event = Event(self.set_buy_price, buy_price)
                        time_sec = (int(hour) * 3600) + curr_day
                        self.add_event(price_event, time_sec)
                    curr_day += buy_price_multiday * SECONDS_IN_DAY
            else:
                for hour, buy_price in buy_price_schedule:
                    price_event = Event(self.set_buy_price, buy_price)
                    time_sec = int(hour) * 3600
                    self.add_event(price_event, time_sec)

    # __________________________________ Messaging Functions _______________________ #

    ##
    # Process a power message from a grid controller. If this utility meter is operational,
    # always provide what is demanded, assuming amount less than maximum output capacity.
    # @param sender_id the
    # @param new_power the new power from the sender's perspective

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        if self._in_operation:
            self._loads[sender_id] = -new_power
            self.recalc_sum_power(prev_power, -new_power)
        else:
            # Not in operation. Respond with 0 power
            self._loads[sender_id] = 0
            self.send_power_message(sender_id, 0)
            self.recalc_sum_power(prev_power, 0)
        wire = self._wires.get(sender_id, None)
        if wire:
            if prev_power > 0:
                self.sum_wire_loss_in(wire, prev_power)
            elif prev_power < 0:
                self.sum_wire_loss_out(wire, prev_power)

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
        # provide the sender exactly what they request
        self._loads[sender_id] = -request_amt
        self.send_power_message(sender_id, -request_amt)

    ##
    # Utility Meter does not process allocate messages.
    # @param sender_id the sender of the allocate message
    # @param allocate_amt the quantity that this device has been allocated to consume

    def process_allocate_message(self, sender_id, allocate_amt):
        pass

    ##
    # This utility meter sends a power message to another device indicating that a certain quantity
    # of power is now flowing across the link. This message should only be in response to receiving a power msg
    # to inform that it must provide a different amount than what was asked.
    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This Utility Meter is connected to no such device")
        self._logger.info(self.build_log_notation(message="power msg to {}".format(target_id),
                                                  tag="power message", value=power_amt))

        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))
    ##
    # This utility meter informs another device of both its current buy price and its current sell price.
    # The buy price information is contained in the message's extra_info field.

    def send_price_message(self, target_id, sell_price, buy_price):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This Utility Meter is connected to no such device")

        self._logger.info(self.build_log_notation(message="price msg to {}".format(target_id),
                                                  tag="price message",
                                                  value="sell {}, buy {}".format(sell_price, buy_price)))

        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE,
                                       value=sell_price, extra_info=buy_price))

    ##
    # Informs all connected devices of the utility meter's buy price
    # @param price the price to broadcast to all connected devices

    def broadcast_price_levels(self, sell_price, buy_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(target_id=device_id, sell_price=sell_price, buy_price=buy_price)

    ##
    # Utility meter currently does not have any specific device calculations to add to the log file
    def device_specific_calcs(self):
        pass

    def last_wire_loss_calc(self):
        for device_id, load in self._loads.items():
            if load:
                wire = self._wires.get(device_id, None)
                if wire:
                    if load > 0:
                        self.sum_wire_loss_in(wire, load)
                    else:
                        self.sum_wire_loss_out(wire, abs(load))
