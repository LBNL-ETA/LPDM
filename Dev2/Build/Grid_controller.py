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
The grid controller is the fundamental building block of the nanogrid simulation.
The role of the grid controller is to manage power flows between the End Use Devices (EUD's),
power sources (such as Utility and PV), storage (batteries), and other grid controllers
(for the purposes of allocating power efficiently between them."""


from Build import Device
from Build import Message
#import price logic.

class GridController(Device):

    # TODO: Add some notion of individual transmit/receive capacity
    # TODO: Add some notion of maximum net_load (e.g all net_load must be covered by battery, so what is max outflow?)

    def __init__(self, device_id, supervisor, price_logic=None):
        super().__init__(self, device_id, supervisor)
        self._allocated = {}  # dictionary of devices and the amount the GC has been allocated from those devices.
        self._neighbor_prices = {}  # dictionary of connected device_id's and their most recent price value
        self._loads = {}  # dictionary of connected device_id's and their current power flow with this GC.
        self._net_load = 0  # the net load the grid controller is sum(power_outflows) - sum(power_inflows).
        self._price_logic = price_logic  # how the grid controller calculates its prices
        self._price = price_logic.initial_price()  # the initial price as set by the price logic

    def process_power_message(self, sender_id, new_power):
        prev_power = self._neighbor_prices[sender_id] if sender_id in self._neighbor_prices.keys() else 0
        self._neighbor_prices[sender_id] = -new_power  # must add negative of sent_power from this GC's reference frame
        self._net_load += (-new_power - prev_power)
        # Check maximum transmit/receive capacity levels, and check maximum net_load concepts. Respond accordingly.

    def process_price_message(self, sender_id, new_price):
        self._neighbor_prices[sender_id] = new_price
        self.modulate_price()
        # TODO: Report this new price to its neighbors?

    def process_request_message(self, sender, request_amt):
        pass  # TODO: Complicated

    def process_allocate_message(self, sender, allocate_amt):
        pass  # TODO: Complicated

    def send_power_message(self, target_id, time, power_amt):
        #  for now, assume target_id means device itself.
        power_message = Message(time, self._device_id, Message.MessageType.POWER, power_amt)
        target_id.receive_message(power_message)

    def send_price_message(self, target_id, time, price):
        #  for now, assume target_id means device itself.
        price_message = Message(time, self._device_id, Message.MessageType.PRICE, price)
        target_id.receive_message(price_message)

    def send_request_message(self, target_id, time, request_amt):
        #  for now, assume target_id means device itself.
        request_message = Message(time, self._device_id, Message.MessageType.REQUEST, request_amt)
        target_id.receive_message(request_message)

    def send_allocate_message(self, target_id, time, allocate_amt):
        #  for now, assume target_id means device itself.
        allocate_message = Message(time, self._device_id, Message.MessageType.ALLOCATE, allocate_amt)
        target_id.receive_message(allocate_message)

    def on_allocated(self, sender_id, allocate_amt):
        self._allocated[sender_id] = allocate_amt  # record how much that device sent in the
        self.modulate_consumption()


    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what it's local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    #
    def modulate_price(self):
        # something like self._price = self.price_logic.calculate_price(neighbor_prices.items() #this it tuples. list?
        pass

    ##
    # The GC is looking to provide or receive power.

    def seek_power(self, time, power_amt):
        gcs = filter(lambda d : isinstance(d, GridController), self._connected_devices)
        #assumes connected devices is device list.
        if gcs:
            for device in gcs:
                ##SHOULD BE IN ORDER OF PRICE. MAYBE we should  separate into buy and provide power methods.
                self.send_request_message(time, device, )
