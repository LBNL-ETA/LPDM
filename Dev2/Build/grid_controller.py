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
from Build.battery import Battery
from abc import ABCMeta, abstractmethod
#import price logic.


class GridController(Device):

    # TODO: Add some notion of individual transmit/receive capacity
    # @param device_id a unique id for this device. "gc" will be prefix for the provided id. Caller is responsible
    # for ensuring the uniqueness of this id.
    # @param price logic a string name of a grid controller price logic class, which contains an initial price as well
    # as a differential threshold for when a GC should broadcast changes in price
    # @param min_response_threshold_ratio the percentage of max battery (dis)charge rate to use as a minimum allocate
    # response for request messages.
    # @param battery battery connected with this Grid Controller (could represent multiple batteries).

    def __init__(self, device_id, supervisor, msg_latency=0, time=0,
                 price_logic=None, battery=None, min_alloc_response_threshold=1, connected_devices=None):
        # identifier = "gc{}".format(device_id)
        super().__init__(device_id, "Grid Controller", supervisor, msg_latency, time, connected_devices)

        # dictionary of devices and the amount the GC has allocated/been allocated by/to them.
        # negative values are how much this GC has allocated to provide, positive for this GC to take.
        self._allocated = {}

        # dictionary of devices and unprovided requests that this device has received from them.
        # negative values are requests for this GC to provide, positive are for this GC to receive.
        self._requested = {}

        self._loads = {}  # dictionary of devices and the current load of the GC with that device.
        self._neighbor_prices = {}  # dictionary of connected device_id's and their most recent price value
        self._battery = battery  # the battery contained within this grid controller. Communicates every minute.
        # the minimum allocate response to a negative request message (for this device to receive)
        self._threshold_alloc_in = min_alloc_response_threshold * battery.get_max_charge_rate()
        # the minimum allocate response to a positive request message (for this device to provide)
        self._threshold_alloc_out = min_alloc_response_threshold * battery.get_max_discharge_rate()

        # TODO: Let these have input parameters
        if price_logic == "weighted_average":
            self._price_logic = GCWeightedAveragePriceLogic()
        #  TODO: elif price_logic == "MarginalPrice":
        else:
            raise ValueError("attempted to initialize grid controller with invalid price logic")
        self._price = self._price_logic.initial_price() if self._price_logic else 0.0

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

        self._logger.info(self.build_log_notation(message="turn off", tag="turn off", value="1"))
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

    ##
    # Processes a request message from an EUD or another GC.
    # Allocates to receive/provide at minimum an amount of trickle power, and rest equal to what is has available.
    # @param sender_id the sender of the request message
    # @param request_amt the quantity of power requested from perspective of message sender
    def process_request_message(self, sender_id, request_amt):
        if request_amt == 0:
            self.send_allocate_message(sender_id, 0)  # always allow power flows to cease
            return
        provide, unprovided = self.request_response(request_amt)
        # Note: May provide more than asked for, which recipient can consume up to at any point.
        self.send_allocate_message(sender_id, provide)  # negative if allocating to send, positive if to receive.
        self._requested[sender_id] = unprovided
        # TODO: Raise the price accordingly to whatever you didn't provide (self.modulate_price())
        # TODO: self.modulate_power() --  or maybe wait on this function until a later moment.

    def process_allocate_message(self, sender_id, allocate_amt):
        self._allocated[sender_id] = allocate_amt  # so we can consume or provide up to that amount of power anytime
        # TODO: self.modulate_power() -- still unbuilt

    ##
    # Sends a power message to another device
    # @param target_id the recipient of the power message
    # @param power_amt the quantity of the new power flow from this device's perspective

    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_log_notation(message="power msg to {}".format(target_id),
                                                  tag="power message", value=power_amt))

        self.change_load(target_id, power_amt)
        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    def send_price_message(self, target_id, price):
        if target_id in self._connected_devices.keys():
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_log_notation(message="price msg to {}".format(target_id),
                                                  tag="price message", value=price))
        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE, price))

    def send_request_message(self, target_id, request_amt):
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_log_notation(message="request msg to {}".format(target_id),
                                                  tag="request message", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    def send_allocate_message(self, target_id, allocate_amt):
        if target_id in self._connected_devices.keys():
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.info(self.build_log_notation(message="allocate msg to {}".format(target_id),
                                                  tag="allocate message", value=allocate_amt))
        self._allocated[target_id] = allocate_amt
        target_device.receive_message(Message(self._time, self._device_id, MessageType.ALLOCATE, allocate_amt))

    # Broadcasts the new price to all of its connected devices.
    # @param new_price the new price to broadcast to all devices
    def broadcast_new_price(self, new_price):
        for device_id in self._connected_devices.keys():
            self.send_price_message(device_id, new_price)

    #  ______________________________________Internal State Functions _________________________________#

    ##
    # Update the current state of the battery. Call this function every five minutes or on price change.
    # Informs the battery of its average prices and hourly prices so that the battery can determine its charge
    # preference accordingly, and recalculate its current state of charge

    def update_battery(self):
        self._battery.update_state(self._time, self._price, self._price_logic.get_average_price(),
                                   self._price_logic.get_hourly_prices())

    ##
    # Call this function every hour during the running of the simulation. This will reevaluate the current running
    # hourly price and total average price statistics so that it can
    def update_price_calcs(self):
        self._price_logic.update_hourly_prices()
        self._price_logic.update_average_price()


    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what its local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    # TODO: Make price logic. For now, do not call this.
    def modulate_price(self):
        old_price = self._price
        self.update_price_calcs()
        self._price = self._price_logic.calc_price(self._neighbor_prices, self._loads, self._requested, self._allocated)
        self._logger.info(self.build_log_notation(message="GC price changed to {}".format(self._price),
                                                  tag="price_change", value=self._price))
        # broadcast only if significant change price.
        if self._price - old_price >= self._price_logic.get_price_announce_threshold():
            self.broadcast_new_price(self._price)

    ##
    # Instantaneous supply-demand balance function, so that the net load at any given time remains at zero.
    # To be called after this GC receives a power message.
    # The GC may not provide the entire requested amount of power if it is not able.
    # See docs for an in-depth description of reasoning.
    #
    # @param source_id the sender of the new amount of power.
    # @param prev_source_power previous amount of a power flow from this GC's perspective
    # @param source_demanded_power the new amount of the power flow from this GC's perspective.

    def balance_power(self, source_id, prev_source_power, source_demanded_power):
        power_change = source_demanded_power - prev_source_power
        if power_change == 0:
            return
        remaining = power_change

        utility_meters = [key for key in self._connected_devices.keys() if key.startswith("utm")]
        # If there is power in from utility and the power change is positive (must accept more), reduce that utm flow.
        if power_change > 0:
            for utm in utility_meters:
                if self._loads.get(utm, 0) > 0:
                    prev_utm_load = self._loads[utm]
                    self.change_load(utm, max((prev_utm_load - remaining), 0))
                    new_utm_load = self._loads[utm]
                    self.send_power_message(utm, new_utm_load)
                    remaining -= (prev_utm_load - new_utm_load)

        # Try adding all the remaining demand onto the battery
        if self._battery:
            self.update_battery()  # make sure we have updated state of charge
            remaining -= self._battery.add_load(remaining)

        if remaining:
            if len(utility_meters):
                utm = utility_meters[0]
                prev_utm_load = self._loads[utm] if utm in self._loads.keys() else 0
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
            if provided > 0:
                self._logger.info(self.build_log_notation(message="could only input {}W".format(provided),
                                                          tag="insufficient power in", value=provided))
            else:
                self._logger.info(self.build_log_notation(message="could only output {}W".format(provided),
                                                          tag="insufficient power out", value=provided))
            self.send_power_message(source_id, provided)

    ##
    # Sees what the GC has freely available to increase from its existing allocates, and what it is liable to
    # provide to other devices
    # @return the current balance of power among allocate levels

    def get_allocate_assets(self):
        assets = 0  # diff. of amount the device has been allocated to receive and amount it is currently taking
        for dev_id, allocated in self._allocated.items():
            if allocated > 0:  # allotted to receive
                assets += max(allocated - self._loads.get(dev_id, 0), 0)
        return assets

    def get_allocate_liabilities(self):
        liabilities = 0  # diff. of amount device has allocated to provide and amount it is currently providing
        for dev_id, allocated in self._allocated.items():
            if allocated < 0:
                liabilities -= min(allocated - self._loads.get(dev_id, 0), 0)
        return liabilities

    ##
    # Determines how much this GC responds to a power request.
    # @return a tuple of provided, unprovided, where provided is the amount of power this device has
    # allocated (positive to receive, negative to provide), and unprovided is the amount of power this device
    # could not handle at this time.
    def request_response(self, request_amt):
        self.update_battery()
        trickle_power = 50  # TODO: Change this to global grid controller variable.
        if request_amt > 0:  # must provide a negative quantity (this device to distribute)
            desired_response = self._battery.get_desired_power() - self.get_allocate_assets()
            provide = max(min(desired_response, -self._threshold_alloc_out, -trickle_power), -request_amt)
            unprovided = request_amt + provide  # provide is negative
            return provide, unprovided
        else:  # must provide positive quantity (this device to receive)
            desired_response = self._battery.get_desired_power() + self.get_allocate_liabilities()
            provide = min(max(desired_response, self._threshold_alloc_in, trickle_power), -request_amt)
            unprovided = -request_amt - provide
            return provide, unprovided

    ##
    # This is the crux function that determines how a GC balances its power flows at a given time.
    # Called upon significant event changes and at regular intervals to help the GC balance its powerflows.
    #

    def modulate_power(self):
        # TODO: Read flow below. This is CRUX FUNCTION, HIGHLY COMPLICATED. CONSIDER DIFFERENT OPTIONS.
        # Equivalent to the recalc argument in the Grid Controller Operation and Messaging model.
        # Returns a value, available, which is after load balancing how much it has available to distribute.
        # If it still is in need of power, this quantity will be 0.

        net_load = self._power_in - self._power_out
        # modulate_target is the net load that the GC is seeking to charge or discharge the battery.

        power_adjust = self._battery.get_desired_power() - net_load  # how much to seek to adjust net load.

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

    # ________________________________LOGGING SPECIFIC FUNCTIONALITY______________________________#

    def device_specific_calcs(self):

        # Write out all consumptions statistics
        if self._battery:
            self._logger.info(self.build_log_notation(
                message="battery sum charge wh",
                tag="battery sum charge wh",
                value=self._battery.sum_charge_wh
            ))

            self._logger.info(self.build_log_notation(
                message="battery sum discharge wh",
                tag="battery sum discharge wh",
                value=self._battery.sum_discharge_wh
            ))

""" A class to determine the Grid Controller's Price Logic"""


class GridControllerPriceLogic(metaclass=ABCMeta):

    ##
    # Returns the devices initial price level
    @abstractmethod
    def initial_price(self):
        pass

    ##
    # A method to determine the minimum price difference which should cause the grid controller to broadcast
    # its new price to a specified subset of its connected devices.
    # TODO: Return tuple of price and time_diff to determine minimum time change before announcing
    @abstractmethod
    def get_price_announce_threshold(self):
        pass

    ##
    # Calculates what this current GC's price is based on some combination of the price of its neighbors,
    # the current request and allocated amounts,
    @abstractmethod
    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None):
        pass

    ##
    # Gets the predicted price of this grid controller at the specified time (in seconds)
    @abstractmethod
    def get_forecast_price(self, time):
        pass

    ##
    # Given the current time of the device, sets the hourly prices of the GC accordingly.
    # This function should be called every hour by the GC, as well as when the GC's price changes.
    @abstractmethod
    def update_hourly_prices(self, time):
        pass

    ##
    # Returns the hourly prices of this grid controller.
    # These price values may be weighted by the implementing logic.
    @abstractmethod
    def get_hourly_prices(self):
        pass

    # TODO: Evaluation of price in context of the price history.
    ##
    # Updates the average time of the grid controller
    @abstractmethod
    def update_average_price(self, time):
        pass

    ##

    @abstractmethod
    def get_average_price(self):
        pass

""" 

Grid controller price logic class which uses a weighted price based on the time that price was maintained to calculate
its average hourly prices and average price statistics. 

"""


class GCWeightedAveragePriceLogic(GridControllerPriceLogic):

    # TODO: Hourly prices renamed to price history. Change to accept non-hour time intervals.

    def __init__(self):
        self._initial_price = 0.1
        self._price_announce_threshold = 0.02
        self._current_price = self._initial_price
        self._hourly_prices = [self._initial_price for i in range(24)]
        self._hourly_average_price = 0.
        self._total_average_price = 0.
        self._last_price_update_time = 0  # the time in the hour when the price was last updated

    def initial_price(self):
        return self._initial_price

    def get_price_announce_threshold(self):
        return self._price_announce_threshold

    ##
    # Predicts the price based on the previous observed price at this hour.
    def get_forecast_price(self, time):
        (day, seconds) = divmod(time, (24 * 60 * 60))
        (hour, seconds) = divmod(seconds, (60 * 60))
        return self._hourly_prices[hour]

    def get_hourly_prices(self):
        return self._hourly_prices

    ##
    # Call this method at least every hour to ensure that the GC's hourly prices are up to date.
    def update_hourly_prices(self, time):
        secs_into_hour = time % 3600
        if secs_into_hour == 0:
            secs_into_hour = 3600

        time_diff = time - self._last_price_update_time  # should always be less than or equal to an hour
        if time_diff > 3600:
            raise ValueError("Missed an hourly value calculation")

        prev_secs_into_hour = self._last_price_update_time % 3600

        prev_sum_price = self._hourly_average_price * prev_secs_into_hour
        self._hourly_average_price = (prev_sum_price + (time_diff * self._current_price)) / secs_into_hour
        self._last_price_update_time = time

    def update_average_price(self, time):
        time_diff = time - self._last_price_update_time
        prev_sum_price = self._total_average_price * self._last_price_update_time
        self._total_average_price = (prev_sum_price + (time_diff * self._current_price)) / time

    def get_average_price(self):
        return self._total_average_price

    ##
    # Calculates this GC's Price as a function of the prices of its power sources, weighted by the fraction
    # of this GC's total power in that
    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None):

        if neighbor_prices and loads:
            total_load_in = 0.0
            sum_price = 0.0
            for source, load in loads:
                if load > 0:  # receiving power from this entity
                    neighbor_price = neighbor_prices.get(source, 0)
                    if neighbor_price:
                        total_load_in += load
                        sum_price += neighbor_price * load
            if total_load_in:
                return sum_price / total_load_in
        # insufficient information or no current loads in, return starting price
        return self._initial_price



    ##
    #
    """
    class GCMarginalPriceLogic:

        # TODO: CHANGE THE LAST UPDATE TIME TO A HARD VALUE, and modify update hourly prices value.

        def __init__(self, initial_price=0.1, price_differential=.02, price_history_segments=24):
            self._initial_price = 0.1
            self._price_differential = 0.02
            self._current_price = self._initial_price
            self._price_history = [self._initial_price for i in range(price_history_segments)]
            self._segment_average_price = 0.
            self._total_average_price = 0.
            self._last_price_update_time = 0  # the time in the hour when the price was last updated

        def initial_price(self):
            return self._initial_price

        def get_price_differential(self):
            return self._price_differential

        ##
        # Predicts the price based on the previous observed price at this hour.
        def get_forecast_price(self, time):
            (day, seconds) = divmod(time, (24 * 60 * 60))
            (hour, seconds) = divmod(seconds, (60 * 60))
            return self._hourly_prices[hour]

        def get_segment_prices(self):
            return self._segment_prices

        def update_segment_prices(self, time):
            segment_length =
            secs_into_hour = time % 3600
            time_diff = secs_into_hour - self._last_price_update_time

            prev_sum_price = self._hourly_average_price * self._last_price_update_time
            self._hourly_average_price = (prev_sum_price + (time_diff * self._current_price)) / secs_into_hour
            self._last_price_update_time = secs_into_hour

        def update_average_price(self, time):
            time_diff = time - self._last_price_update_time
            prev_sum_price = self._total_average_price * self._last_price_update_time
            self._total_average_price = (prev_sum_price + (time_diff * self._current_price)) / time

        def get_average_price(self):
            return self._total_average_price

        ##
        # Calcutes this GC's Price as a function of the prices of its power sources, weighted by the fraction
        # of this GC's total power in that
        def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None):

            if neighbor_prices and loads:
                total_load_in = 0.0
                sum_price = 0.0
                for source, load in loads:
                    if load > 0:  # receiving power from this entity
                        neighbor_price = neighbor_prices.get(source, 0)
                        if neighbor_price:
                            total_load_in += load
                            sum_price += neighbor_price * load

                if total_load_in:
                    return sum_price / total_load_in
                else:
                    return


            else:
                return self._initial_price
    """