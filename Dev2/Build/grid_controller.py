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


from Build.device import Device
from Build.message import Message, MessageType
from Build.supervisor import Supervisor
from Build.priority_queue import PriorityQueue
from Build.battery import Battery
from Build.battery import BatteryChargingPreference as BCP
#import price logic.


class GridController(Device):

    # TODO: Add some notion of individual transmit/receive capacity
    # TODO: Add some notion of maximum net_load (e.g all net_load must be covered by battery, so what is max outflow?)
    
    # @param price logic contains an initial price as well as a differential threshold for when a GC should broadcast
    # changes in price
    # @param battery battery connected with this Grid Controller (could represent multiple batteries).

    def __init__(self, device_id, supervisor, price_logic=None, battery=None):
        super().__init__(device_id, "Grid Controller", supervisor)
        self._allocated = {}  # dictionary of devices and the amount the GC has allocated/been allocated by/to them.
        self._loads = {}  # dictionary of devices and the current load of the GC with that device.
        self._neighbor_prices = {}  # dictionary of connected device_id's and their most recent price value
        self._net_load = 0  # the net load the grid controller is sum(power_outflows) - sum(power_inflows).
        self._desired_net_load = 0 # the flow the GC is seeking, equal to BCP * Battery.preferred_(dis)charge_rate
        self._price_logic = price_logic  # how the grid controller calculates its prices
        self._price = price_logic.initial_price() if price_logic else None # the initial price as set by the price logic
        self._battery = battery  # the battery contained within this grid controller.

    ##
    # @param sender_id the device which sent the power message
    # @param new_power the new power value from the perspective of the message sender.

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self._loads[sender_id] = -new_power  # must add negative of sent_power from this GC's reference frame
        self._net_load += (-new_power - prev_power)
        # Check maximum transmit/receive capacity levels, and check maximum net_load concepts. Respond accordingly.

    def process_price_message(self, sender_id, new_price):
        self._neighbor_prices[sender_id] = new_price
        self.modulate_price(new_price) # if price significantly changed, will broadcast this price to all neighbors. 
        self.modulate_power()  # TODO: THIS FUNCTION IS UNBUILT.

    def process_request_message(self, sender, request_amt):
        pass  # TODO: Complicated

    def process_allocate_message(self, sender, allocate_amt):
        pass  # TODO: Complicated

    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        power_message = Message(self._time, self._device_id, MessageType.POWER, power_amt)
        target.receive_message(power_message)

    def send_price_message(self, target_id, price):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        price_message = Message(self._time, self._device_id, MessageType.PRICE, price)
        target.receive_message(price_message)

    def send_request_message(self, target_id, request_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        request_message = Message(self._time, self._device_id, MessageType.REQUEST, request_amt)
        target.receive_message(request_message)

    def send_allocate_message(self, target_id, allocate_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        allocate_message = Message(self._time, self._device_id, MessageType.ALLOCATE, allocate_amt)
        target.receive_message(allocate_message)

    # Broadcasts the new price to all of its connected devices. 
    def broadcast_new_price(self, new_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(device_id, new_price)

    def on_allocated(self, sender_id, allocate_amt):
        self._allocated[sender_id] = allocate_amt  # record how much that device sent in the
        #self.modulate_power() #TODO: THIS FUNTION IS UNBUILT


    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what its local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    #
    def modulate_price(self):
        old_price = self._price
        self._price = self._price_logic.calculate_price(self._neighbor_prices.values())
        if self._price - old_price >= self._price_logic.diff_threshold:
            self.broadcast_new_price(self._price)

    ##
    # This is the crux function that determines how a GC balances its power flows.
    #

    def modulate_power(self):
        # TODO: Read flow below. This is CRUX FUNCTION, HIGHLY COMPLICATED. CONSIDER DIFFERENT OPTIONS.
        pass

    ##
    # The GC is looking to provide or receive power.
    """
    def seek_to_sell_power(self, time, power_amt):
        gcs = filter(lambda d : d.startswith('GC'), self._connected_devices.keys())
        #assumes connected devices is device list.
        if gcs:
            for device in gcs:
                ##SHOULD BE IN ORDER OF PRICE. MAYBE we should  separate into buy and provide power methods.
                self.send_request_message(time, device, )
                
    def seek_to_buy_power(self, time, power_amt):
        gcs = filter(lambda d: 
    """

    """

PROPOSED ORDER OF PRIORITIES TO BALANCE POWER LEVELS SEEKING. 

--Step 1: Increase all values up to their current allocate limit. 
--Step 2: 
    -Are you connected to utility? If so, use it to recallibrate. If not, step 3.
--Step 3: 
    Can battery sustain the current deficit?
    --Yes, within comfortable range (more than 20% charge): Raise Price Slightly. 
    Request more power from all neighbors with price less than yours. 
    Once you have received allocate messages, max out your requests starting from least
    expensive to most expensive. 
    
    --Yes, within critical range (less than 20%): Double Price. 
    Request more power from all neighbors with price less than yours. 
    Once you have received allocate messages, max out your requests starting from least
    expensive to most expensive.
    
    --NO: Double Price. Request power. Reduce your output to other GC's.  
    
    --STILL NO: REDUCE output to EUD's. 
    
    --STILL NO: SHUT DOWN. 
    
    
    def seek_to_sell_power(self, time, power_amt):
        gcs = filter(lambda d : d.startswith('GC'), self._connected_devices.keys())
        #assumes connected devices is device list.
        if gcs:
            for device in gcs:
                ##SHOULD BE IN ORDER OF PRICE. MAYBE we should  separate into buy and provide power methods.
                self.send_request_message(time, device, )
                
    def seek_to_buy_power(self, time, power_amt):
        gcs = filter(lambda d: 
    """

    ###   ____TESTING FUNCTIONS____###
    def add_power_in(self):
        self.set_power_in(10)  # FOR TESTING