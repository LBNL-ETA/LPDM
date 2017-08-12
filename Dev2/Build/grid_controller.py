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
    # @param device_id a unique id for this device. "gc" will be prefix for the provided id. Caller is responsible
    # for ensuring the uniqueness of this id.
    # @param price logic contains an initial price as well as a differential threshold for when a GC should broadcast
    # changes in price
    # @param battery battery connected with this Grid Controller (could represent multiple batteries).

    def __init__(self, device_id, supervisor, read_delay=0, time=0, price_logic=None, battery=None,
                 connected_devices=None):
        # identifier = "gc{}".format(device_id)
        super().__init__(device_id, "Grid Controller", supervisor, read_delay, time, connected_devices)
        self._allocated = {}  # dictionary of devices and the amount the GC has allocated/been allocated by/to them.
        self._requested = {}  # dictionary of devices and requests that this device has received from them.
        self._loads = {}  # dictionary of devices and the current load of the GC with that device.
        self._neighbor_prices = {}  # dictionary of connected device_id's and their most recent price value
        self._price_logic = price_logic  # how the grid controller calculates its prices
        self._price = price_logic.initial_price() if price_logic else None # the initial price as set by the price logic
        self._battery = battery  # the battery contained within this grid controller. Communicates every minute.

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

    ##
    # Turns the grid controller on, registering it with all of its connected devices.
    # @param connected_devices the devices that this GC is connected to (default to already connected devices)
    def turn_on(self, connected_devices=None):
        if connected_devices is None:  # already has its connected devices. Engage them.
            self.engage(self._connected_devices.values())
        else:
            self.engage(connected_devices)
        if self._price:
            self.broadcast_new_price(self._price)  # inform neighbors of its initial price.

    ##
    # Shuts down the grid controller. Stop power flows. Send messages to all connected devices to reset their
    # negotiations with this grid controller to zero.
    def turn_off(self):
        self.set_power_in(0)
        self.set_power_out(0)
        self.disengage()

        self._logger.info(self.build_message(message="turn off", tag="turn off", value="1"))
        # send power message of 0 to all devices. send allocate message of 0 to all devices.
        # send request messages of 0 to all of them. Then, unregister with all.

    ##
    #
    # Changes a load with a registered device. Call this before sending a power message so as to
    # calculate the load you can actually handle considering capacities.
    # @param sender_id the device to associate the load with
    # @param new_load the value of the new load
    # TODO: Add a maximum channel capacity for this load.
    # @return the amount added to the load
    def change_load(self, sender_id, new_load):
        prev_load = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self.recalc_sum_power(prev_load, new_load)
        self._loads[sender_id] = new_load
        return new_load - prev_load



    #  ______________________________________ Messaging/Interactive Functions_________________________________#

    ##
    # @param sender_id the device which sent the power message
    # @param new_power the new power value from the perspective of the message sender.

    def process_power_message(self, sender_id, new_power):
        prev_power = self._loads[sender_id] if sender_id in self._loads.keys() else 0
        self.balance_power(sender_id, prev_power, -new_power)  # process new power from perspective of receiver.

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
        self._logger.info(self.build_message(message="power msg to {}".format(target_id),
                                             tag="power message", value=power_amt))

        prev_power = self._loads[target_id] if target_id in self._connected_devices.keys() else 0
        self.recalc_sum_power(prev_power, power_amt)

        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    def send_price_message(self, target_id, price):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_message(message="price msg to {}".format(target_id),
                                              tag="price message", value=price))
        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE, price))

    def send_request_message(self, target_id, request_amt):
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_message(message="request msg to {}".format(target_id),
                                              tag="request message", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    def send_allocate_message(self, target_id, allocate_amt):
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_message(message="allocate msg to {}".format(target_id),
                                              tag="allocate message", value=allocate_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.ALLOCATE, allocate_amt))

    # Broadcasts the new price to all of its connected devices.
    # @param new_price the new price to broadcast to all devices
    def broadcast_new_price(self, new_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(device_id, new_price)

    def on_allocated(self, sender_id, allocate_amt):
        self._allocated[sender_id] = allocate_amt  # so we can consume or provide up to that amount of power anytime
        # self.modulate_power() # TODO: THIS FUNCTION IS UNBUILT

    #  ______________________________________Internal State Functions _________________________________#

    ##
    # Update the current state of the battery. Call this function every five minutes or on price change.
    # Battery will recalculate it
    # @param the time to set the battery to

    def update_battery(self, time):
        self._battery.update_state(time, self._price)
    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what its local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    # TODO: Make price logic. For now, do not call this.
    def modulate_price(self):
        old_price = self._price
        self._price = self._price_logic.calculate_price(self._neighbor_prices.values())
        self._logger.info(self.build_message(message="GC price changed to {}".format(self._price),
                                             tag="price_change", value=self._price))
        if self._price - old_price >= self._price_logic.diff_threshold:  # broadcast only if significant change price.
            self.broadcast_new_price(self._price)

    ##
    # Instantaneous supply-demand balance function, so that the net load at any given time remains at zero.
    # See docs for an in-depth description of reasoning.
    # @param source_id the sender of the new amount of power.
    # @param prev_source_power the previous amount of power this device was sending to the source of the power change
    # @param source_demanded_power the new amount of power this device is being instructed
    # to send to the source of the power change
    # NOTE: The GC may not provide the entire requested amount of power if it is not able.
    #

    def balance_power(self, source_id, prev_source_power, source_demanded_power):
        power_change = source_demanded_power - prev_source_power
        if power_change == 0:
            return
        remaining = power_change

        utility_meters = [key for key in self._connected_devices.keys() if key.startswith("utm")]
        # If there is power in from utility and the power change is negative, reduce that flow.
        for utm in utility_meters:
            if self._loads.get(utm, 0) < 0:
                prev_utm_load = self._loads[utm]
                self.change_load(utm, min((prev_utm_load - remaining), 0))
                new_utm_load = self._loads[utm]
                self.send_power_message(utm, new_utm_load)
                remaining += (new_utm_load - prev_utm_load)

        # Try adding all the remaining demand onto the battery
        if self._battery:
            self._battery.update_state(self._time, self._price)  # make sure we have updated state of charge
            remaining -= self._battery.add_load(remaining)

        if remaining:
            if len(utility_meters):
                utm = utility_meters[0]
                prev_utm_load = self._loads[utm] if utm in self._loads.keys() else 0
                # (below) The additional amount you are able to provide to the utility meter (neg. if receive).
                self.change_load(utm, prev_utm_load - remaining)
                new_utm_load = self._loads[utm]
                self.send_power_message(utm, new_utm_load)

                remaining += (new_utm_load - prev_utm_load)  # what we were able to get from utility meter.
                self.change_load(source_id, source_demanded_power - remaining)  # send what we were able to get from utm

                # add the unprovided power as a request to address later.
                unprovided = source_demanded_power - self._loads[source_id]
                if unprovided:
                    self._requested[source_id] = unprovided

            else:
                # no utm, not able to provide for the demanded power. Send a new power message saying what you can give.
                self.change_load(source_id, source_demanded_power - remaining)

                # add the unprovided power as a request.
                unprovided = source_demanded_power - self._loads[source_id]
                if unprovided:
                    self._requested[source_id] = unprovided
        else:
            self.change_load(source_id, source_demanded_power)
            # NOTE: won't consider case where GC wire capacity is limiting and battery discharge is not, not realistic.

        # inform recipient if power provided is not what was expected
        provided = self._loads[source_id]
        if provided != source_demanded_power:
            self._logger.info(self.build_message(message="GC only could provide {}W".format(provided),
                                                 tag="undistributed power", value=provided))
            self.send_power_message(source_id, provided)

    ##
    # This is the crux function that determines how a GC balances its power flows at a given time.
    # Called upon significant event changes and at regular intervals to help the GC balance its powerflows.
    #

    def modulate_power(self):
        # TODO: Read flow below. This is CRUX FUNCTION, HIGHLY COMPLICATED. CONSIDER DIFFERENT OPTIONS.
        # Equivalent to the recalc argument in the Grid Controller Operation and Messaging model.
        # Returns a value, available, which is after load balancing how much it has available to distribute.
        # If it still is in need of power, this quantity will be 0.

        net_load = self._power_out - self._power_in
        # modulate_target is the net load that the GC is seeking to charge or discharge the battery.
        if self._battery.get_charging_preference() == 1:
            modulate_target = self._battery.get_preferred_discharge_rate()
        elif self._battery.get_charging_preference() == -1:
            modulate_target = -self._battery.get_preferred_charge_rate()
        else:
            modulate_target = 0

        power_adjust = modulate_target - net_load  # how much to seek to adjust net load.

        if power_adjust < 0:
            self.seek_to_obtain_power(power_adjust)
        if power_adjust > 0:
            self.seek_to_distribute_power(power_adjust)

    def seek_to_obtain_power(self, power_adjust):
        # Step 1: Increase all allocate values up to their maximum.

        for device_id in self._allocated.keys():
            pass
        pass 

    def seek_to_distribute_power(self, power_adjust):
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

    # ________________________________TESTING/LOGGING_FUNCTIONS FUNCTIONS______________________________#

    def add_power_in(self):
        self.set_power_in(10)  # FOR TESTING

    def device_specific_calcs(self):

        # Write out all consumptions statistics
        if self._battery:
            self._logger.info(self.build_message(
                message="battery sum charge wh",
                tag="battery sum charge wh",
                value=self._battery.sum_charge_wh
            ))

            self._logger.info(self.build_message(
                message="battery sum discharge wh",
                tag="battery sum discharge wh",
                value=self._battery.sum_discharge_wh
            ))




