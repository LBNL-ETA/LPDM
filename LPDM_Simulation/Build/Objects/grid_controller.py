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


from abc import ABCMeta, abstractmethod

from Build.Objects.grid_equipment import GridEquipment
from Build.Objects.utility_meter import UtilityMeter
from Build.Objects.converter.converter import Converter

from Build.Simulation_Operation.message import Message, MessageType, MessageRedirect
from Build.Simulation_Operation.event import Event
from Build.Simulation_Operation.support import SECONDS_IN_DAY, SECONDS_IN_HOUR, nonzero_power, delta
from Build.Objects.device import Device


class GridController(GridEquipment):

    TRICKLE_POWER = 2  # Allow fluctuations of power within 2 watts without rebalancing. All devices can consume this.

    # TODO: Add some notion of individual transmit/receive capacity
    # @param device_id a unique id for this device, must begin with "gc". Creator is responsible
    # for ensuring the uniqueness of this id.
    # @param price logic a string name of a grid controller price logic class, which contains an initial price as well
    # as a differential threshold for when a GC should broadcast changes in price
    # @param price logic interval how often to update the battery
    # @param min_response_threshold_ratio the percentage of max battery (dis)charge rate to use as a minimum allocate
    # response for request messages.
    # @param battery battery connected with this Grid Controller (could represent multiple batteries).

    def __init__(self, device_id, supervisor, time=0, msg_latency=0,
                 price_logic="", price_logic_interval=SECONDS_IN_HOUR, starting_price=0.1,
                 price_announce_threshold=0.01, battery=None, min_alloc_response_threshold=1.0,
                 schedule=None, total_runtime=SECONDS_IN_DAY, connected_devices=None):

        super().__init__(device_id=device_id, device_type="grid_controller", supervisor=supervisor,
                         time=time, msg_latency=msg_latency, schedule=schedule, connected_devices=connected_devices)

        # dictionary of devices and the amount the GC has allocated/been allocated by/to them.
        # Negative values are how much this GC has allocated to others, positive for this GC has been allocated to take.
        self._allocated = {}

        # dictionary of devices and requests that this device has received from them.
        # Only is added to when this grid controller could not provide the full quantity in response.
        # Negative values are requests this GC has been asked provide,
        # positive are requests this GC has made to other devices.
        self._requested = {}

        # dictionary of devices and the current load of the GC with that device.
        self._loads = {}
        # dictionary of connected device_id's and their most recent price value. For utm, this only contains sell price.
        self._neighbor_prices = {}
        # A dictionary of utilities to their sell and buy prices, respectively.
        self._utility_prices = {}
        # keep track of which devices are utility meters
        # device could also be a Converter connected to more than 1 utility meter
        self._connected_utility_meters = []
        # the battery contained within this grid controller.
        if battery:
            self._battery = battery
        else:
            raise ValueError("Tried to make a grid controller without a battery. Not acceptable!")

        # the minimum allocate response to a request message
        self._minimum_allocate = min_alloc_response_threshold * battery.get_max_discharge_rate()

        self._total_runtime = total_runtime

        if price_logic == "weighted_average":
            self._price_logic = GCWeightedAveragePriceLogic(price_logic_interval, starting_price,
                                                            price_announce_threshold)
        elif price_logic == "marginal_price":
            self._price_logic = GCMarginalPriceLogic(price_logic_interval, starting_price,
                                                     price_announce_threshold)
        elif price_logic == "marginal_price_b":
            self._price_logic = GCMarginalPriceLogicB(price_logic_interval, starting_price,
                                                     price_announce_threshold)
        else:
            raise ValueError("attempted to initialize grid controller with invalid price logic")

        self._price = self._price_logic.get_initial_price() if self._price_logic else 0.0
        self.setup_price_calc_schedule(self._price_logic.get_price_history_interval(), total_runtime)

        self.setup_battery_update_schedule(self._battery.get_update_frequency(), total_runtime)
        self.setup_modulation_schedule(total_runtime)
    
    def init(self):
        super().init()
        self.build_utility_meter_list()
    
    def build_utility_meter_list(self):
        """Build a list of utility meters"""
        for d_id, d in self._connected_devices.items():
            if isinstance(d, UtilityMeter) or (isinstance(d, Converter) and d.has_utm()):
                self._connected_utility_meters.append(d_id)

    #  ______________________________________Maintenance Functions______________________________________ #

    # def device_is_utm(self, device_id):
    #     "Determine if a given device_id is a utility meter, or is a converter connected to a utility meter"
    #     items = [d for d in self._connected_utility_meters if d.utm_device_id == device_id]
    #     return len(items) > 0

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

        self._logger.info(self.build_log_notation(message="turn off", tag="turn_off", value="1"))
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
        prev_load = self._loads[sender_id] if sender_id in self._loads else 0
        self.recalc_sum_power(prev_load, new_load)
        self._loads[sender_id] = new_load
        self._logger.info(self.build_log_notation(message="load changed for {} to {}".format(sender_id, new_load),
                                                   tag="load change", value=new_load))
        return new_load - prev_load

    ##
    # Recalculates the average price history at every given interval.
    # @param[in] price_history_interval how frequently prices should be recalculated.
    # @param[in] total_runtime the total runtime of the simulation, this will setup events up until that time
    def setup_price_calc_schedule(self, price_history_interval, total_runtime):
        curr_time = self._time
        if price_history_interval <= 0:
            return
        while curr_time < total_runtime:
            self.add_event(Event(self.update_average_price_calcs), curr_time)
            curr_time += price_history_interval

    ##
    # Sets up the events to recalculate the battery's charge preference every certain period of time.
    # @param update_frequency how frequently prices should be recalculated.
    # @param total_runtime the total runtime of the simulation, this will setup events up until that time
    def setup_battery_update_schedule(self, update_frequency, total_runtime):
        curr_time = self._time
        if update_frequency <= 0:
            return
        while curr_time < total_runtime:
            self.add_event(Event(self.update_battery), curr_time)
            curr_time += update_frequency

    ##
    # Every 5 minutes, reevaluate this Grid Controller's loads with modulate power and seek to optimize
    # the distribution.
    # @param total_runtime the length of the simulation in seconds.

    def setup_modulation_schedule(self, total_runtime):
        modulation_frequency = 300  # Default 5 Minutes.
        curr_time = self._time
        while curr_time < total_runtime:
            self.add_event(Event(self.modulate_power), curr_time)
            curr_time += modulation_frequency

    #  ______________________________________ Messaging/Interactive Functions_________________________________#

    ##
    # Override of the device register message function. When it receives a register message, also responds
    # with information about this GC's price.
    #
    # @param sender_id the sender of the message informing of registering.
    # @param value positive if sender is registering negative if unregistering

    def process_register_message(self, message):
        if message.sender_id in self._connected_devices:
            sender = self._connected_devices[message.sender_id]
        else:
            sender = self._supervisor.get_device(message.sender_id)  # not in local table. Ask supervisor for the pointer to it.
        self.register_device(sender, message.sender_id, message.value)
        if message.value > 0:
            self.send_price_message(message.sender_id, self._price)

    ##
    # Processes a power message, indicating power flows have changed. First, instantaneously responds
    # to that power flow with balance power. Then, adjusts its price based on new power flows, and
    # finally tries to shift its power in a more optimal way.
    # @param sender_id the device which sent the power message
    # @param new_power the new power value from the perspective of the message sender.

    def process_power_message(self, message):
        self._logger.info(
            self.build_log_notation(
                message="POWER message from {}".format(message.sender_id),
                tag="power_msg_in",
                value=message.value
        ))
        prev_power = self._loads[message.sender_id] if message.sender_id in self._loads else 0
        self.balance_power(message.sender_id, prev_power, -message.value)  # process new power from perspective of receiver.
        if delta(message.value, prev_power) > self.TRICKLE_POWER:  # don't recalibrate for power changes smaller than this
            self.modulate_price()
            self.modulate_power()

    ##
    # Processes a price message received from another device, modifying its own price based on its price logic.
    #
    # @param sender_id the sender of the message
    # @param price the local price received from the message sender

    def process_price_message(self, message):
        # if message.sender_id.startswith("utm"):  # Remember sell price, buy_price pair from utility meters
        # sender_id = message.redirect.original_sender_id if isinstance(message.redirect, MessageRedirect) else message.sender_id
        if message.sender_id in self._connected_utility_meters:
            self._utility_prices[message.sender_id] = (message.value, message.extra_info)
        self._neighbor_prices[message.sender_id] = message.value
        self.modulate_price()  # if price significantly changed, will broadcast this price to all neighbors.
        self.modulate_power()

    ##
    # Processes a request message from an EUD or another GC, and allocates in response whatever matches its
    # @param sender_id the sender of the request message
    # @param request_amt the quantity of power requested from perspective of message sender
    def process_request_message(self, message):
        if message.value < 0:
            return  # Invalid request. Must be positive.
        if message.value == 0:
            self.send_allocate_message(message.sender_id, 0)  # always allow power flows to cease
            return
        elif not nonzero_power(self._requested.get(message.sender_id, 0) + message.value):
            return  # Already have noted this request and am working on it.
        provide = self.request_response(message.value)
        # Note: May provide more than asked for, which recipient can consume up to at any point.
        self.send_allocate_message(message.sender_id, provide)  # Positive
        self._requested[message.sender_id] = -message.value
        self.modulate_price()

    ##
    # Process an allocate message from another grid controller.

    def process_allocate_message(self, message):
        if message.value < 0:
            self._logger.info("ignored negative allocate message from {}".format(message.sender_id))
            return
        self._allocated[message.sender_id] = message.value  # so we can consume or provide up to that amount of power anytime
        # TODO: self.modulate_power()?

    ##
    # Sends a power message to another device
    # @param target_id the recipient of the power message
    # @param power_amt the quantity of the new power flow from this device's perspective

    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
        self.change_load(target_id, power_amt)
        # add in additional wire loss
        # if wire_loss is non-zero, then there's a wire attached
        wire_loss = self.calculate_wire_loss(target_id, power_amt)
        if wire_loss:
            if power_amt:
                # if power_amt is non-zero, add in additional wire loss
                power_amt += wire_loss
                self.update_wire_loss_in(target_id, abs(wire_loss))
            else:
                # power_amt is zero so no wire loss
                self.update_wire_loss_in(target_id, 0)
        self._logger.info(self.build_log_notation(message="POWER to {}".format(target_id),
                                                  tag="power_msg", value=power_amt))

        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    #
    # Informs another device of this grid controller's price
    def send_price_message(self, target_id, price):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
        self._logger.info(self.build_log_notation(message="PRICE to {}".format(target_id),
                                                  tag="price_msg", value=price))
        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE, price))

    ##
    # Requests to receive a given amount of power from another device.
    def send_request_message(self, target_id, request_amt):
        if target_id in self._connected_devices:
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
        self._logger.info(self.build_log_notation(message="REQUEST to {}".format(target_id),
                                                  tag="request_msg", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    ##
    # Allocates a given quantity of power to be provided to another device.
    def send_allocate_message(self, target_id, allocate_amt):
        if target_id in self._connected_devices:
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
        self._logger.info(self.build_log_notation(message="ALLOCATE to {}".format(target_id),
                                                  tag="allocate_msg", value=allocate_amt))
        self._allocated[target_id] = -allocate_amt
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
                                   self._price_logic.get_interval_prices())

        # If the state is no longer possible (power drawn out with non-positive state-of-charge, or charging at full
        # charge, we must immediately reduce).
        curr_battery_load = self._battery.get_load()
        if self._battery.get_current_soc() <= 0 and curr_battery_load < 0:
            self._battery.clear_load()
            for source, load in self._loads.copy().items():  # Copy so that we don't modify the dictionary during iter
                if load < 0:
                    # Treat each load like it is a new demand. Try to recalibrate without using the utility meter.
                    self.balance_power(source, 0, load)
        elif self._battery.get_current_soc() >= 1 and curr_battery_load > 0:
            self._battery.clear_load()
            for source, load in self._loads.copy().items():  # Copy so that we don't modify the dictionary during iter
                if load > 0:
                    # Treat each load like it is a new demand. Try to recalibrate without using the utility meter.
                    self.balance_power(source, 0, load)

    ##
    # Call this function every hour during the running of the simulation. This will reevaluate the current running
    # hourly price and total average price statistics so that it can base its current price based on those.
    def update_average_price_calcs(self):
        self._price_logic.update_prices(self._time)

    ##
    # Recalculates the price with the Grid Controller's price logic, and then sets the current price value.
    def recalculate_price(self):
        battery_power_adjust = self._battery.get_optimal_charge_rate() - self._battery.get_load()
        self._price = self._price_logic.calc_price(neighbor_prices=self._neighbor_prices,
                                                   loads=self._loads, requested=self._requested,
                                                   allocated=self._allocated,
                                                   desired_battery_power=battery_power_adjust)
        self._price_logic.set_current_price(self._price)

    ##
    # Calculate this after a device has received a price message.
    # Iterates through the current prices of its neighbors and finds what its local price should be.

    # @param price_logic the pricing logic being used by the grid controller
    def modulate_price(self):
        old_price = self._price
        self.update_average_price_calcs()  # update the previous average price information
        self.recalculate_price()  # use the price logic to evaluate a new price
        if self._price != old_price:  # log this if the price changed.
            self._logger.info(self.build_log_notation(message="price changed to {}".format(self._price),
                                                      tag="price change", value=self._price))
            # broadcast only if significant change price.
            price_delta = delta(self._price, old_price)
            if price_delta >= self._price_logic.get_price_announce_threshold():
                self.broadcast_new_price(self._price)

    ##
    # Instantaneous supply-demand balance function, so that the net load at any given time remains at zero.
    # To be called after this GC receives a power message, indicating external power flows have changed.
    # The GC may not provide the entire requested amount of power if it is not able.
    # See docs for an in-depth description of reasoning of this algorithm.
    #
    # @param source_id the sender of the new amount of power.
    # @param prev_source_power previous amount of a power flow from this GC's perspective
    # @param source_demanded_power the new amount of the power flow to another device from this GC's perspective.

    def balance_power(self, source_id, prev_source_power, source_demanded_power):
        power_change = source_demanded_power - prev_source_power
        if power_change == 0:
            return
        remaining = power_change

        # If there is power in from utility and the power change is positive (must accept more), reduce that utm flow.
        # Likewise, if we are selling to utm and power change is negative, reduce how much we sell.
        """ THIS WAS AN OPTIMIZATION. CAN BE REMOVED OR PUT IN FLAGGED LOGIC"""
        for utm_id in self._connected_utility_meters:
            if power_change > 0:
                # must accept more.
                if self._loads.get(utm_id, 0) > 0:
                    prev_utm_load = self._loads[utm_id]
                    self.change_load(utm_id, max((prev_utm_load - remaining), 0))
                    new_utm_load = self._loads[utm_id]
                    self.send_power_message(utm_id, new_utm_load)
                    remaining -= (prev_utm_load - new_utm_load)
                    if not nonzero_power(remaining): # An insignificant quantity is remaining. Stop talking to utms
                        break
            elif power_change < 0:
                # must provide more
                if self._loads.get(utm_id, 0) < 0:
                    prev_utm_load = self._loads[utm_id]
                    self.change_load(utm_id, min((prev_utm_load - remaining), 0))
                    new_utm_load = self._loads[utm_id]
                    self.send_power_message(utm_id, new_utm_load)
                    remaining -= (prev_utm_load - new_utm_load)
                    if not nonzero_power(remaining):
                        break

        # TODO: Try raising all allocate values up to their limits. Move battery adjustment to after utility meter try.
        # Try adding all the remaining demand onto the battery
        if nonzero_power(remaining) and self._battery:
            self.update_battery()  # make sure we have updated state of charge
            remaining -= self._battery.add_load(remaining)

        if nonzero_power(remaining):
            if len(self._connected_utility_meters):
                utm_id = self._connected_utility_meters[0]

                prev_utm_load = self._loads[utm_id] if utm_id in self._loads else 0
                self.change_load(utm_id, prev_utm_load - remaining)
                new_utm_load = self._loads[utm_id]
                self.send_power_message(utm_id, new_utm_load)

                # what we were able to get from utility meter.
                remaining += (new_utm_load - prev_utm_load)
                self.change_load(source_id, source_demanded_power - remaining)  # send what we were able to get from utm

                # add the unprovided power as a request to address later.
                unprovided = source_demanded_power - self._loads[source_id]
                if unprovided:
                    self._requested[source_id] = source_demanded_power
            else:
                # no utm, not able to provide for the demanded power. Send a new power message saying what you can give.
                self.change_load(source_id, source_demanded_power - remaining)

                # add the unprovided power as a request.
                unprovided = source_demanded_power - self._loads[source_id]
                if unprovided:
                    self._requested[source_id] = source_demanded_power
        else:
            self.change_load(source_id, source_demanded_power)

        # inform recipient if power provided is not what was expected
        provided = self._loads[source_id]
        if nonzero_power(provided - source_demanded_power):
            if provided > 0:
                self._logger.info(self.build_log_notation(message="could only input {}W".format(provided),
                                                          tag="insufficient power in", value=provided))
            else:
                self._logger.info(self.build_log_notation(message="could only output {}W".format(provided),
                                                          tag="insufficient power out", value=provided))
            self.send_power_message(source_id, provided)

    ##
    # Sees what the GC has freely available to increase from its existing allocates compared to existing loads
    # @return quantity of freely available power from existing allocates

    def get_allocate_assets(self):
        assets = 0  # diff. of amount the device has been allocated to receive and amount it is currently taking
        for dev_id, allocated in self._allocated.items():
            if allocated > 0:  # allocated to receive
                assets += max(allocated - self._loads.get(dev_id, 0), 0)
        return assets

    ##
    # Sees what the GC is liable to provide other devices because of its allocation to other devices that are
    # not being fully utilized in current loads.
    # @return quantity of excess allocate liabilities

    def get_allocate_liabilities(self):
        liabilities = 0  # diff. of amount device has allocated to provide and amount it is currently providing
        for dev_id, allocated in self._allocated.items():
            if allocated < 0:
                liabilities -= min(allocated - self._loads.get(dev_id, 0), 0)
        return liabilities

    ##
    # Determines how much this GC responds to a power request. See documentation for reasoning.
    # @return how much this device will provide in respond to that request message (negative value)
    def request_response(self, request_amt):
        self.update_battery()
        if request_amt > 0:  # This device is being asked to distribute
            desired_response = self.get_allocate_assets() - self._battery.get_optimal_charge_rate()
            return max(desired_response, self._minimum_allocate)
        else:  # Invalid request
            return 0

    ##
    # This function determines how the Grid Controller tries to optimize its loads to satisfy its battery preference
    # Called upon significant event changes and at regular intervals to help the GC balance its powerflows.
    #
    def modulate_power(self):

        battery_load = self._battery.get_load()  # equivalent to battery's current load.
        desired_net_load = self._battery.get_optimal_charge_rate()

        power_adjust = desired_net_load - battery_load  # Negative if seeking to distribute extra, positive if to accept.
        if nonzero_power(power_adjust):
            if power_adjust < 0:
                self.seek_to_distribute_power(-power_adjust)
            elif power_adjust > 0:
                self.seek_to_obtain_power(power_adjust)
        # TODO: Add a load shifting component that optimizes existing loads.

    ##
    # Grid controller is seeking to obtain the remaining amount of power for itself to consume.
    # Currently, only goes to the utility meters if it is connected and tries to shift power onto them,
    # does not do any shifting on less expensive power sources/grid controller optimization.
    # @param power_to_obtain the amount of power this grid controller would like to obtain from other sources. Must
    # be positive.

    #
    def seek_to_obtain_power(self, power_to_obtain):
        if power_to_obtain <= 0:
            return
        remaining = power_to_obtain
        for utm_id in self._connected_utility_meters:
            prev_utm_load = self._loads.get(utm_id, 0)
            self.change_load(utm_id, prev_utm_load + remaining)
            new_utm_load = self._loads[utm_id]
            self.send_power_message(utm_id, new_utm_load)
            remaining -= (new_utm_load - prev_utm_load)
            if remaining <= 0:
                break
        self._battery.add_load(power_to_obtain - remaining)
        # Set battery to whatever amount could be offset.

    ##
    # The grid controller is seeking to distribute some quantity of power to its connected devices.
    # Currently, only tries to sell it off the utility meter, and whatever cannot be distributed is added back to
    # battery.
    #
    # @param power_to_distribute the amount of power that this grid controller would like to distribute to other sources
    # must be a positive value.
    #
    def seek_to_distribute_power(self, power_to_distribute):
        if power_to_distribute <= 0:
            return  # Invalid quantity
        remaining = power_to_distribute
        for utm_id in self._connected_utility_meters:
            prev_utm_load = self._loads.get(utm_id, 0)
            self.change_load(utm_id, prev_utm_load - remaining)
            new_utm_load = self._loads[utm_id]
            self.send_power_message(utm_id, new_utm_load)
            remaining -= (prev_utm_load - new_utm_load)
            if remaining <= 0:
                break
        self._battery.add_load(-power_to_distribute + remaining)

    def last_wire_loss_calc(self):
        for (device_id, wire_loss_rate) in self._wire_loss_info_in.items():
            if wire_loss_rate:
                self.update_wire_loss_in(device_id, wire_loss_rate)
        for (device_id, wire_loss_rate) in self._wire_loss_info_out.items():
            if wire_loss_rate:
                self.update_wire_loss_out(device_id, wire_loss_rate)
        pass


    # ________________________________LOGGING SPECIFIC FUNCTIONALITY______________________________#

    ##
    # The grid controller is also responsible for writing its batteries calculations. Additionally, the grid controller
    # checks the accuracy of its calculations by making sure the the difference in battery charge levels fully
    # covers the difference in the power in and power out levels.

    def device_specific_calcs(self):

        # Allow for more accumulated error over the course of longer runs.
        MARGIN_OF_ERROR = .01 * (self._total_runtime / SECONDS_IN_DAY)

        # Write out all battery consumptions statistics
        if self._battery:
            self._logger.info(self.build_log_notation(
                message="battery sum charge Wh",
                tag="power_calcs",
                value=self._battery.sum_charge_wh
            ))

            self._logger.info(self.build_log_notation(
                message="battery sum discharge Wh",
                tag="power_calcs",
                value=self._battery.sum_discharge_wh
            ))
            # Ensure that the change in power is completely covered by the battery for valid calculations
            power_differential = (self._battery.sum_discharge_wh - self._battery.sum_charge_wh) - \
                                 (self._sum_power_out - self._sum_power_in)
            valid_calc = abs(power_differential) <= MARGIN_OF_ERROR
            self._logger.info(self.build_log_notation(
                message="valid power balance: {}".format(valid_calc),
                tag="valid_calcs",
                value=valid_calc
            ))

    #  _______________________________ PRICE LOGICS ________________________________________________#

##
# The abstract class for all grid controller price logics. All abstract methods must be implemented by all price logics.


class GridControllerPriceLogic(metaclass=ABCMeta):

    ##
    # @param price_history_interval the length of the interval to calculate the average price for and store in memory
    # (e.g. if 3600, then store hourly average prices).
    # @param initial price the initial price of this grid controller
    # @param price_announce_threshold the difference in prices before announcing your new local price to neighbors

    def __init__(self, price_history_interval, initial_price, price_announce_threshold):
        if price_history_interval == 0:
            raise ValueError("cannot have 0 second price interval")
        self._initial_price = initial_price
        self._price_announce_threshold = price_announce_threshold
        self._current_price = self._initial_price
        self._price_history_interval = price_history_interval

        # calculate rounded up number of intervals
        daily_price_history_len, rem = divmod(SECONDS_IN_DAY, price_history_interval)
        if rem:
            daily_price_history_len += 1

        self._interval_prices = [self._initial_price for i in range(daily_price_history_len)]
        self._total_average_price = self._initial_price
        self._last_price_update_time = 0  # the time in the hour when the price was last updated

    ##
    # Returns the devices initial price level
    def get_initial_price(self):
        return self._initial_price

    ##
    # A method to determine the minimum price difference which should cause the grid controller to broadcast
    # its new price to a specified subset of its connected devices.
    def get_price_announce_threshold(self):
        return self._price_announce_threshold

    ##
    # Gets the predicted price of this grid controller at the specified time (in seconds)
    def get_forecast_price(self, time):
        (day, seconds) = divmod(time, SECONDS_IN_DAY)
        (interval_num, seconds) = divmod(seconds, self._price_history_interval)
        return self._interval_prices[interval_num]

    ##
    # Gets the length of a price intervals
    def get_price_history_interval(self):
        return self._price_history_interval

    ##
    # Given the current time of the device, uses the current price to set the interval prices of the GC accordingly.
    # This function should be called every interval duration by the GC, as well as when the GC's price changes.
    # @param the current time of the device
    def update_interval_prices(self, time):
        # Calculate which interval we are in and how many seconds into that interval we are
        (day, seconds) = divmod(time, SECONDS_IN_DAY)
        (interval_num, secs_into_interval) = divmod(seconds, self._price_history_interval)

        time_diff = time - self._last_price_update_time  # should always be less than or equal to interval length
        if time_diff > self._price_history_interval:
            raise ValueError("Missed an interval value calculation")

        # Calculate the interval when the last calculation happened so we know how much time has passed
        (prev_day, prev_seconds) = divmod(self._last_price_update_time, SECONDS_IN_DAY)
        (prev_interval_num, secs_into_previous_interval) = divmod(prev_seconds, self._price_history_interval)

        if prev_interval_num == interval_num and prev_day == day:  # we are in the same interval. Need to average.
            prev_sum_price = self._interval_prices[interval_num] * secs_into_previous_interval
        else:
            prev_sum_price = 0

        if secs_into_interval:
            self._interval_prices[interval_num] = (prev_sum_price +
                                                  (time_diff * self._current_price)) / secs_into_interval
        else:
            self._interval_prices[interval_num] = self._current_price

    ##
    # Updates the average time of the grid controller
    # @param time the current time of the device
    def update_average_price(self, time):
        if time:
            time_diff = time - self._last_price_update_time
            prev_sum_price = self._total_average_price * self._last_price_update_time
            self._total_average_price = (prev_sum_price + (time_diff * self._current_price)) / time
        else:
            self._total_average_price = self._current_price

    ##
    # Returns the interval prices of this grid controller.
    # These price values may be weighted by the implementing logic.
    def get_interval_prices(self):
        return self._interval_prices

    ##
    # Sets the current price to use in the price logic for calculations. Call this function whenever the
    # grid controller's local price changes.
    # @param price
    def set_current_price(self, price):
        self._current_price = price

    ##
    # Updates the interval and average price calculations stored in this price logic for this GC.
    # These calculations are dependent on the current price stored in the price logic.
    # @param time the current time stored in the price logic
    def update_prices(self, time):
        self.update_interval_prices(time)
        self.update_average_price(time)
        self._last_price_update_time = time

    ##
    # @return the average price for this price logic
    def get_average_price(self):
        return self._total_average_price

    ##
    # Calculates what this current GC's price is based on some combination of the price of its neighbors,
    # the current request and allocated amounts. Varies between different implementations of price logics.
    # @param neighbor_prices the dictionary of connected device id's and their prices
    # @param loads dictionary of connected device id's and current loads with those devices
    # @param requested dictionary of connected device id's and current requests to and from those devices
    # @param allocated the dictionary of connected device id's and allocated by and to those devices.
    # @param desired_battery_charge the difference of current desired battery power flow and desired batt. power flow
    # @return the calculated price based on the input variables.
    @abstractmethod
    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None,
                   desired_battery_power=0):
        pass


""" 

Grid controller price logic class which uses a weighted price based on the time that price was maintained to calculate
its average hourly prices and average price statistics. 

Functional Review: Produces strange results because it is based entirely on current loads, rather than on any potential
power that this grid controller has access to. For example, this algorithm works effectively when the Grid Controller 
is currently drawing in power from the utility meter or another grid controller to support its current load balance. 
However, most of the time when it is simply drawing on the battery to funnel to other entities, it doesn't have the 
necessary information and simply relies on its initial price as a fallback value, which doesn't seem to make sense. 
Hence, it seems that marginal price logic will be superior here. 

Additionally, contains no logic for implement any concepts of 'local scarcity', i.e. battery charging preference 
compared to current power flows is not considered. 
"""


class GCWeightedAveragePriceLogic(GridControllerPriceLogic):

    ##
    # @param price_history_interval the length of the interval to calculate the average price for and store in memory
    # @param initial price the initial price of this grid controller
    # @param price_announce_threshold the difference in prices before announcing your new local price to neighbors

    def __init__(self, price_history_interval, initial_price, price_announce_threshold):
        super().__init__(price_history_interval, initial_price, price_announce_threshold)

    ##
    # Calculates this GC's Price as a function of the prices of its power sources, weighted by the fraction
    # of this GC's total power in that device is providing. If there are no current loads in, defaults to the initial
    # price
    # @param neighbor_prices the dictionary of connected device id's and their prices
    # @param loads dictionary of connected device id's and current loads with those devices
    # @param requested dictionary of connected device id's and current requests to and from those devices
    # @param allocated the dictionary of connected device id's and allocated by and to those devices.
    # @param desired_battery_charge the difference of current desired battery power flow and desired batt. power flow

    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None, desired_battery_power=0):

        if neighbor_prices and loads:
            total_load_in = 0.0
            sum_price = 0.0
            for source, load in loads.items():
                if load > 0:  # receiving power from this entity
                    neighbor_price = neighbor_prices.get(source, 0)
                    if neighbor_price >= 0:
                        total_load_in += load
                        sum_price += (neighbor_price * load)
            if total_load_in:
                return sum_price / total_load_in
        # insufficient information on neighbor prices or no current loads in, return starting price
        return self._initial_price


""" 
Finds the minimum price among the sources that this device has been allocated to receive from, or from the utility. 
If it doesn't meet any of these conditions, return its initial price.
 
TODO: This logic does not consider the battery charging preference in its calculations. This should be added. 
"""


class GCMarginalPriceLogic(GridControllerPriceLogic):

    ##
    # @param price_history_interval the length of the interval to calculate the average price for and store in memory
    # @param initial price the initial price of this grid controller
    # @param price_announce_threshold the difference in prices before announcing your new local price to neighbors

    def __init__(self, price_history_interval, initial_price, price_announce_threshold):
        super().__init__(price_history_interval, initial_price, price_announce_threshold)

    ##
    #
    # Price is a function of the neighbors prices who have allocated to this device and utility meter prices.
    # @param neighbor_prices the dictionary of connected device id's and their prices
    # @param loads dictionary of connected device id's and current loads with those devices
    # @param requested dictionary of connected device id's and current requests to and from those devices
    # @param allocated the dictionary of connected device id's and allocated by and to those devices.
    # @param desired_battery_charge the difference of current desired battery power flow and desired batt. power flow
    # @return the calculated price based on the input variables.
    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None, desired_battery_power=0):
        min_price = float('inf')

        # Find the cheapest price amongst the devices we've been allocated to receive from or utility meters
        for source, price in neighbor_prices.items():
            if allocated.get(source, -1) > 0 or source.startswith("utm"):
                if price < min_price:
                    min_price = price
        if min_price != float('inf'):
            return min_price
        else:
            return self._initial_price  # Not enough information from other prices

""" Same as above, but seeks to find the marginal price level that will satisfy all open requests and the 
desired difference in battery power levels. If there is insufficient allocations, returns 1.1 * highest price"""


class GCMarginalPriceLogicB(GridControllerPriceLogic):

    ##
    # @param price_history_interval the length of the interval to calculate the average price for and store in memory
    # @param initial price the initial price of this grid controller
    # @param price_announce_threshold the difference in prices before announcing your new local price to neighbors

    def __init__(self, price_history_interval, initial_price, price_announce_threshold):
        super().__init__(price_history_interval, initial_price, price_announce_threshold)

    ##
    #
    # Price is a function of the neighbors prices who have allocated to this device and utility meter prices.
    # @param neighbor_prices the dictionary of connected device id's and their prices
    # @param loads dictionary of connected device id's and current loads with those devices
    # @param requested dictionary of connected device id's and current requests to and from those devices
    # @param allocated the dictionary of connected device id's and allocated by and to those devices.
    # @param desired_battery_charge the difference of current desired battery power flow and desired batt. power flow
    # (positive if wants to charge more, negative if wants to output more)
    # @return the calculated price based on the input variables.

    def calc_price(self, neighbor_prices=None, loads=None, requested=None, allocated=None, desired_battery_power=0):
        total_requested_out = 0  # positive record of how much this device has been requested to provide out

        # Calculate how much this device owes to provide.
        for requested in requested.values():
            if requested < 0:
                total_requested_out -= requested

        # Calculate how much has been requested vs. how much we want to change battery, this is our total power
        # flow shift amount that we want to calculate the marginal price of satisfying.
        remaining = total_requested_out + desired_battery_power
        prices_from_cheapest = sorted(neighbor_prices.items(), key=lambda x: x[1])
        # We are looking to distribute power and there is insufficient current demand.
        # Lower our price to below current cheapest price level to allow to sell
        if remaining < 0:
            return 0.9 * prices_from_cheapest[0][1]

        marginal_price = float('inf')
        # Find the cheapest price amongst the devices we've been allocated to take from.
        for source, price in prices_from_cheapest:
            if allocated.get(source, -1) > 0:
                remaining -= allocated[source]
                marginal_price = price
                if remaining < 0:
                    break

        # Subset to only the utility meter prices (we can take infinite without allocation)
        utm_prices = {device: price for device, price in neighbor_prices.items() if device.startswith("utm")}
        if utm_prices:
            for utm, price in utm_prices:
                if price < marginal_price:
                    marginal_price = price
        else:
            # There are no utility meters and we can't get enough from other sources.
            # Raise it higher than all other sources.
            if remaining > 0 and marginal_price != float('inf'):
                return 1.1 * marginal_price

        if marginal_price != float('inf'):
            return marginal_price

        else:
            return self._initial_price  # not enough information from other prices


