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
        self._requested = {}  # dictionary of devices and requests that this device has received from them.
        self._loads = {}  # dictionary of devices and the current load of the GC with that device.
        self._neighbor_prices = {}  # dictionary of connected device_id's and their most recent price value
        self._net_load = 0  # the net load the grid controller is sum(power_outflows) - sum(power_inflows).
        self._desired_net_load = 0  # the flow the GC is seeking, equal to BCP * Battery.preferred_(dis)charge_rate
        self._price_logic = price_logic  # how the grid controller calculates its prices
        self._price = price_logic.initial_price() if price_logic else None # the initial price as set by the price logic
        self._battery = battery  # the battery contained within this grid controller.

    #  ______________________________________Maintenance Functions______________________________________ #

    ##
    # Method to be called when device is leaving the grid, and is seeking to unregister with other devices.
    # Clears all other devices' records for this device before requesting to unregister and stop receiving messages.

    def disengage(self):
        for device_id in self._connected_devices.keys():
            self.send_request_message(device_id, 0)
            self.send_allocate_message(device_id, 0)
            self.send_power_message(device_id, 0)
            self.send_register_message(device_id, -1)

    def turn_on(self, connected_devices):
        if self._connected_devices.values(): # already has its connected devices. Engage them.
            self.engage(self._connected_devices.values()) # self.e


        # broadcast price to all neighbors.
        pass

    def turn_off(self):
        self.set_power_in(0)
        self.set_power_out(0)
        self.disengage()

        self._logger.info(self.build_message(message="turn off", tag="turn off", value="1"))
        # send power message of 0 to all devices. send allocate message of 0 to all devices.
        # send request messages of 0 to all of them. Then, unregister with all.






    #  ______________________________________ Messaging/State Functions_________________________________#

    ##
    # @param sender_id the device which sent the power message
    # @param new_power the new power value from the perspective of the message sender.

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self._loads[sender_id] = -new_power  # must add negative of sent_power from this GC's reference frame
        self._net_load += (-new_power - prev_power)
        # Check maximum transmit/receive capacity levels, and check maximum net_load concepts. Respond accordingly.

    ##
    # Processes a price message received from another device, modifying its own price based on its price logic.
    #
    # @param sender_id the sender of the message
    # @param price the local price received from the message sender

    def process_price_message(self, sender_id, price):
        self._neighbor_prices[sender_id] = price
        self.modulate_price()  # if price significantly changed, will broadcast this price to all neighbors.
        self.modulate_power()  # TODO: THIS FUNCTION IS UNBUILT.

    def process_request_message(self, sender_id, request_amt):
        # TODO: Calculate how much it can allocate given that request. Use modulate_price function.
        self._requested[sender_id] = request_amt
        # available = self.modulate_power().
        # Temporarily, we will just allocate the entire requested amount.
        self.send_allocate_message(sender_id, request_amt)

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
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    def send_allocate_message(self, target_id, allocate_amt):
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS. 
        target_device.receive_message(Message(self._time, self._device_id, MessageType.ALLOCATE, allocate_amt))

    # Broadcasts the new price to all of its connected devices.
    # @param new_price the new price to broadcast to all devices
    def broadcast_new_price(self, new_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(device_id, new_price)

    def on_allocated(self, sender_id, allocate_amt):
        self._allocated[sender_id] = allocate_amt  # so we can consume or provide up to that amount of power anytime
        # self.modulate_power() # TODO: THIS FUNTION IS UNBUILT

    #  ______________________________________Internal Calculation Functions _________________________________#


    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what its local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    #
    def modulate_price(self):
        old_price = self._price
        self._price = self._price_logic.calculate_price(self._neighbor_prices.values())
        if self._price - old_price >= self._price_logic.diff_threshold: # significant change in local price.
            self.broadcast_new_price(self._price)


    ##
    # Instantaneous supply-demand balance function, so that the net_load at any given time remains at zero.
    #

    def balance_power(self):
        pass
        # TODO: This is implemented in Mike's code. Check it out and see if portable.

    ##
    # This is the crux function that determines how a GC balances its power flows at a given time.
    # Called upon significant event changes and at regular intervals to help the GC balance its powerflows.
    #

    def modulate_power(self):
        # TODO: Read flow below. This is CRUX FUNCTION, HIGHLY COMPLICATED. CONSIDER DIFFERENT OPTIONS.
        # Equivalent to the recalc argument in the Grid Controller Operation and Messaging model.
        # Returns a value, available, which is after load balancing how much it has available to distribute.
        # If it still is in need of power, this quantity will be 0.
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

Called whenever 
(1) A load changes
(2) Internal price changes
(3) Receives a request 
(4) Is allocated power 
(5) Also internally calculated every set period of time. 

First priority: Are current levels in balance? 

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
    
Second priority: Negotiation balances (new allocate received, new request received). 
    
    
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

    # ________________________________TESTING FUNCTIONS______________________________#

    def add_power_in(self):
        self.set_power_in(10)  # FOR TESTING