

################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0"
# Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

"""
    Implementation of a Grid Controller
"""

from device_manager import DeviceManager
from power_source_manager import PowerSourceManager
from power_buyer_manager import PowerBuyerManager
from device.base.power_source import PowerSource
from device.base.power_source_buyer import PowerSourceBuyer
from device.base.device import Device
from device.simulated.battery import Battery
from device.simulated.battery.state_preference import StatePreference
from device.simulated.utility_meter import UtilityMeter
from common.device_class_loader import DeviceClassLoader
from device.scheduler import LpdmEvent
from supervisor.lpdm_event import LpdmBuyPowerPriceEvent, LpdmBuyMaxPowerEvent, LpdmBuyPowerEvent
import logging

class GridController(Device):
    """
    Device implementation of a grid controller.

    Use the battery to try and keep the diesel generator above 70% capacity
    """

    def __init__(self, config):
        """
        Args:
            config (Dict): Dictionary of configuration values for the grid controller

            keys:
                "device_name" (string): Name of the device
                "power_price" (float): Price of power ($/kWh)
                "capacity (float): Maximum available capacity (Watts),
                "diesel_output_threshold" (float): Percentage of output capacity of the diesel generator to keep above using the battery
                "check_battery_soc_rate" (int): Rate at which to update the battery state of charge when charging or discharging (seconds)
                "battery_config" (Dict): Configuration object for the battery attached to the grid controller
        """
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "grid_controller"
        self._device_name = config.get("device_name", "grid_controller")
        self._capacity = config.get("capacity", 3000.0)
        self._static_price = config.get("static_price", False)

        # keep track of the utility meter's online status
        self._is_utility_meter_online = False

        # setup the logic for calculating the gc's price, default to average price
        self._price_logic_class_name = config.get("price_logic_class", "WeightedAveragePriceLogic")
        self._price_logic = None
        self._last_price_change_time = None

        # setup the battery if requested
        self._battery = None
        self.battery_config = config.get("battery", None)

        self._total_load = 0.0

        # setup the managers for devices and power sources
        self.device_manager = DeviceManager()
        self.power_source_manager = PowerSourceManager()
        self.power_buyer_manager = PowerBuyerManager()

        # set up class loader
        self._device_class_loader = DeviceClassLoader()

    def init(self):
        """Initialize the grid controller"""
        self.power_source_manager.set_time(self._time)
        self.set_price_logic()
        self.set_initial_price()
        self.init_battery()
        self.calculate_next_ttie()

    def set_initial_price(self):
        """Set an initial price"""
        if not self._price is None:
            self._hourly_prices.append(self._price)
            self.send_price_change_to_devices()

    def init_battery(self):
        """Setup the battery"""
        if not self.battery_config is None:
            # initialize the battery
            self._battery = Battery(self.battery_config)
            # add it to the power source manager, set its price and capacity
            self.power_source_manager.add(self._battery._device_id, Battery, self._battery)
            self.power_source_manager.set_capacity(self._battery._device_id, 0)
            self.power_source_manager.set_price(self._battery._device_id, self._battery._price)
            # setup the shared objects for events and power sources
            self._battery.set_event_list(self._events)
            self._battery.set_power_source_manager(self.power_source_manager)
            self._battery.set_price_history(self._hourly_prices)
            self._battery.init()
            self._logger.info(self.build_message(message="Initialized the battery."))

    def set_price_logic(self):
        """Set the logic for calculating the GC's price"""
        # get the class object from the class name
        LogicClass = self._device_class_loader.class_for_name(
            "device.simulated.grid_controller.price_logic", self._price_logic_class_name
        )
        # create the object
        self._price_logic = LogicClass(self.power_source_manager)
        self._logger.info(
            self.build_message("Set price logic class to {}".format(LogicClass))
        )

    def set_battery_price(self, new_price):
        """Set's the battery's price"""
        if self._battery:
            self._battery.set_price(new_price)

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        """
        Notification from a device that a power change has occurred.
        Could be from either a power source or an eud.
        If from a power source (Diesel Generator, PV, ...) then it's a change in its power output.
            This should only happen when a device is turing itself off
        If from an EUD then it's a change in it's power consumption.
        """
        self._time = time
        self.power_source_manager.set_time(self._time)
        if self._battery:
            self._battery.set_time(time)

        self._logger.debug(self.build_message(
            message="Power change, source_device_id = {}, new_power = {}".format(source_device_id, new_power),
            tag="receive_power",
            value=new_power
        ))

        price_change = False
        ps = self.power_source_manager.get(source_device_id)
        # is this a power source or an eud?
        if ps:
            # if it's a power source, register its new usage
            # TODO: check capacity?
            if ps.load != new_power:
                self.power_source_manager.set_load(source_device_id, new_power)
                price_change = self.calculate_gc_price()
                self.power_source_update()

        else:
            # this is not a power source so need to add the device's requested power to a power source
            # if add_load returns False, then unable to set power for the device

            # get the change in power for the device
            device = self.device_manager.get(source_device_id)
            # calculate the change in power for the source device
            p_diff = new_power - device.load

            if p_diff == 0:
                # no change in power for the device
                self._logger.debug(
                    self.build_message(message="No change in power for {}".format(source_device_id))
                )
            elif not self.power_source_manager.has_available_power_sources():
                # power for the device has changed but no available power sources
                # set all devices to zero power
                self._logger.info(
                    self.build_message("No power sources available, unable to set load for {}".format(source_device_id))
                )
                # let all the devices know there is no more power available
                self.shutdown()
                self.broadcast_new_power(0.0, source_device_id)
                # for d in self.device_manager.device_list:
                    # self.broadcast_new_power(0.0, d.device_id)
            else:
                # power has changed, either positive or negative
                p = self.device_manager.get(source_device_id)
                p_original = p.load
                self.power_source_manager.add_load(p_diff)
                if self.power_source_update():
                    # successfully added the load
                    self.device_manager.set_load(source_device_id, new_power)
                else:
                    # unable to provide the requested power
                    # TODO: if can't provide power, shutdown ? or restore to previous load?
                    # take the load out of the power source manager
                    self.power_source_manager.add_load(-1 * (p_diff + p_original))
                    self.device_manager.set_load(source_device_id, 0.0)
                    self.broadcast_new_power(0.0, source_device_id)

        self.update_power_purchases()
        if self.calculate_gc_price():
            self.send_price_change_to_devices()
        self.power_source_manager.reset_changed()
        # self.schedule_next_events()
        self.calculate_next_ttie()

    def power_source_update(self):
        """Update the power source manager."""
        # update the battery status
        if self._battery:
            self._battery.update_status()
            self._logger.debug(self.build_message(message="battery_pref", tag="battery_pref", value=self._battery._preference))
            if not self._battery._can_discharge and self._battery._preference == StatePreference.DISCHARGE:
                if self._battery._is_charging:
                    self._battery.stop_charging()
                    self._battery.disable_charge()
                # make the battery available for discharge
                self._battery.enable_discharge()
            elif self._battery._can_discharge and self._battery._preference != StatePreference.DISCHARGE:
                # disable the battery if necessary
                self._battery.disable_discharge()
        # try to optimize the load between the various power sources
        result_success = self.power_source_manager.optimize_load()
        initial_success = result_success
        if not result_success:
            # couldn't optimize the load, try turning off charging
            if self._battery and self._battery._is_charging:
                # if can't add the load and the battery is charging, stop charging and try again
                self._battery.stop_charging()
                self._battery.disable_charge()
                result_success = self.power_source_manager.optimize_load()
        if not result_success:
            # still not able to optimize the load
            # start lowering the power we're selling
            # calculate the amount of power that we need to reduce so load doesn't exceed capacity
            p_diff = self.power_source_manager.total_load() - self.power_source_manager.total_capacity()
            # get the list of devices that are currently purchasing power
            buyers = self.power_buyer_manager.get_buyers()
            # loop through each power purchaser and lower the amount of power purchased
            for buyer in buyers:
                if p_diff > buyer.load:
                    # excess load exceeds what this device is buying
                    p_diff -= buyer.load
                    self.power_source_manager.add_load(-1 * buyer.load)
                    buyer.set_load(0.0)
                else:
                    # device is buying
                    new_load = buyer.load - p_diff
                    p_diff -= new_load
                    self.power_source_manager.add_load(-1 * new_load)
                    buyer.set_load(new_load)
                self.broadcast_buy_power(buyer.device_id, buyer.load)
                if p_diff < 1e-7:
                    break
            result_success = self.power_source_manager.optimize_load()
        if not result_success:
            # still not able to optimize the load
            # start turning off devices until able to proceed
            sorted_devices = sorted(self.device_manager.device_list, lambda a, b: cmp(b.uuid, a.uuid))
            for d in sorted_devices:
                if d.load:
                    self.power_source_manager.remove_load(d.load)
                    d.set_load(0.0)
                    self.broadcast_new_power(0.0, d.device_id)
                    if self.power_source_manager.total_load() <= self.power_source_manager.total_capacity():
                        break
            result_success = self.power_source_manager.optimize_load()

        if initial_success:
            # no errors occured on the initial attempt, can try to charge and sell power
            # check if the battery needs to be charged, charge if available
            if self._battery and not self._battery._is_charging and self._battery._preference == StatePreference.CHARGE:
                self._logger.debug(self.build_message(message="battery_can_charge", tag="bat_can_charge", value=1))
                if self.power_source_manager.can_handle_load(self._battery.charge_rate()):
                    if self._battery._can_discharge:
                        self._battery.disable_discharge()
                    self._battery.enable_charge()
                    self._battery.start_charging()
                    result_success = self.power_source_manager.optimize_load()
                    if not result_success:
                        self._logger.error(self.build_message("Unable to charge battery."))
                        self._battery.stop_charging()
                        self._battery.disable_charge()
                        self.power_source_manager.optimize_load()

        # let any changed power sources know that it needs to change its power output
        for p in self.power_source_manager.get_changed_power_sources():
            # broadcast the messages to the power sources that have changed
            if p.DeviceClass is Battery:
                pass
            else:
                self.broadcast_new_power(p.load, p.device_id)


        return result_success

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        self._time = time
        # check that the price change is from a device supplying power
        # ignore price changes from all other devices
        if self.power_source_manager.get(source_device_id):
            # a power source has changed its price
            self.power_source_manager.set_time(self._time)
            if self._battery:
                # update the battery charge and status
                self._battery.set_time(time)
            if not self._static_price:
                self._logger.debug(
                    self.build_message(
                        message="Price change received (new_price = {}, source_device_id = {}, target_device_id = {})".format(new_price, source_device_id, target_device_id)
                    )
                )
                # set the price for the device
                self.power_source_manager.set_price(source_device_id, new_price)
                if self.power_source_update():
                    # calculate the new gc price
                    if self.calculate_gc_price():
                        # send the new price to the devices if changed
                        self.send_price_change_to_devices()
                    self.power_source_manager.reset_changed()
                    self.update_power_purchases()
                else:
                    # Error occured during load optimization
                    # shut down everything
                    self._logger.error(self.build_message("optimize_load error during price change"))
                    self.shutdown()

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self.power_source_manager.set_time(self._time)
        if self._battery:
            self._battery.set_time(new_time)

        self._logger.debug(self.build_message(
            message="received ttie notice",
            tag="receive_ttie",
            value=new_time
        ))
        self.process_events()
        if self.calculate_gc_price():
            self.send_price_change_to_devices()
        self.schedule_next_events()
        self.calculate_next_ttie()
        self.power_source_manager.reset_changed()
        return

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device registers its capacity to the grid controller it's registered to"""
        self._time = time
        self._logger.debug(self.build_message(
            message="received capacity change {} -> {}".format(source_device_id, value),
            tag="receive_capacity",
            value=value
        ))
        ps = self.power_source_manager.get(source_device_id)
        if ps:
            # handle capacity changes from suppliers of power
            self.power_source_manager.set_time(self._time)
            self.power_source_manager.set_capacity(source_device_id, value)
            if ps.DeviceClass is UtilityMeter:
                if value == 0:
                    self._is_utility_meter_online = False
                    self._logger.debug(self.build_message(
                        message="utility_meter_online",
                        tag="um_online",
                        value=0
                    ))
                else:
                    self._is_utility_meter_online = True
                    self._logger.debug(self.build_message(
                        message="utility_meter_online",
                        tag="um_online",
                        value=1
                    ))
            if self.power_source_update():
                self.power_source_manager.reset_changed()
                # notify any euds of capacity changes
                # the eud checks to see if it should be in operation
                # turns itself on if necessary
                for d in self.device_manager.devices():
                    self.broadcast_new_capacity(self.power_source_manager.total_capacity(), d.device_id)

                if self.calculate_gc_price():
                    # send the new price to the devices if changed
                    self.send_price_change_to_devices()

                self.update_power_purchases()
            else:
                # load exceeds capacity after the new capacity is applied
                self._logger.debug(
                    self.build_message(
                        message="Load exceeds capacity ({} > {})".format(
                            self.power_source_manager.total_load(),
                            self.power_source_manager.total_capacity()
                        ),
                        tag="load_gt_cap",
                        value=1
                    )
                )
                self.shutdown()

    def add_device(self, new_device_id, DeviceClass, uuid):
        "Add a device to the list devices connected to the grid controller"
        if issubclass(DeviceClass, PowerSourceBuyer):
            # add power buyers
            self._logger.info(
                self.build_message(
                    message="connected a power buyer to the gc {} - {} - {}".format(new_device_id, DeviceClass, uuid))
            )
            self.power_buyer_manager.add(new_device_id, DeviceClass)
        elif issubclass(DeviceClass, PowerSource):
            # add power sources
            self._logger.info(
                self.build_message(
                    message="connected a power source to the gc {} - {} - {}".format(new_device_id, DeviceClass, uuid))
            )
            self.power_source_manager.add(new_device_id, DeviceClass)
        else:
            # add regular devices
            self._logger.debug(self.build_message(message="uuid for {}".format(new_device_id), tag="uuid", value=uuid))
            self._logger.info(
                self.build_message(
                    message="connected a device to the gc {} - {}, - {}".format(new_device_id, DeviceClass, uuid))
            )
            self.device_manager.add(new_device_id, DeviceClass, uuid)

    def calculate_gc_price(self):
        """Calculate the price grid controller's price"""
        if self._last_price_change_time == self._time:
            return False
        new_price = self._price_logic.get_price()
        # double the price if utility meter is down
        if not self._is_utility_meter_online and not new_price is None:
            new_price *= 2.0
        self._last_price_change_time = self._time
            # set the new price if it has changed
        if new_price != self._price and not new_price is None:
            self._logger.debug(self.build_message(message="price changed", tag="price", value=new_price))
            self.set_price(new_price)
            self.set_battery_price(new_price)

            return True
        else:
            return False

    def send_price_change_to_devices(self):
        "Sends a change in price notification to the connected devices"
        self._logger.debug(
            self.build_message(
                message="send price change to all devices (new_price = {})".format(self._price),
                tag="send_price_change",
                value="1"
            )
        )
        # send the new price to the non-power-sources
        for d in self.device_manager.devices():
            if not self._price is None:
                self.broadcast_new_price(self._price, d.device_id)

    def shutdown(self):
        """
        Shutdown devices until load no longer exceeds capacity.
        Start shutting down devices with the higher uuid until load <= capacity
        """
        self._logger.info(self.build_message(message="Shutdown", tag="shutdown", value="1"))
        sorted_devices = sorted(self.device_manager.device_list, lambda a, b: cmp(b.uuid, a.uuid))
        for d in sorted_devices:
            if d.load:
                self.power_source_manager.remove_load(d.load)
                d.set_load(0.0)
                self.broadcast_new_power(0.0, d.device_id)
                if self.power_source_manager.total_load() <= self.power_source_manager.total_capacity():
                    break

    def shutdown_all(self):
        """Shutdown the grid, set all loads to zero, notify all devices"""
        self._logger.info(self.build_message(message="Shutdown All", tag="shutdown_all", value="1"))
        # self.power_source_manager.shutdown()
        # self.device_manager.shutdown()
        # notify all devices of change in load -> 0
        for d in self.device_manager.devices():
            if d.load:
                self.power_source_manager.remove_load(d.load)
                d.set_load(0.0)
                self.broadcast_new_power(0.0, d.device_id)

    def process_events(self):
        "Process any events that need to be processed"
        Device.process_events(self)

        remove_items = []
        set_power_sources_called = False

        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "emit_initial_price":
                    self.send_price_change_to_devices()
                    remove_items.append(event)
                elif event.value == "battery_status":
                    self._logger.debug(self.build_message(message="battery_status event found", tag="bat_stat_found", value=1))
                    self.power_source_update()
                    remove_items.append(event)
                elif event.value == "log_end_use_device":
                    self.log_end_use_device()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        # if there's a battery then process its events
        if self._battery:
            self._battery.process_events()
            # self.power_source_manager.optimize_load()

    def schedule_next_events(self):
        "Schedule upcoming events if necessary"
        Device.schedule_next_events(self)
        if self._battery:
            # the battery shares the same event array as the gc
            self._battery.schedule_next_events()
        # schedule the next end-use load log event
        self.schedule_next_end_use_log_event()

    def set_initial_price_event(self):
        """Let all other devices know of the initial price of energy"""
        new_event = LpdmEvent(0, "emit_initial_price")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == "emit_initial_price", self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def calculate_next_ttie(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        the_event = None
        for event in self._events:
            if ttie == None or event.ttie < ttie:
                ttie = event.ttie
                the_event = event

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcast_new_ttie(ttie)

    def process_supervisor_event(self, the_event):
        """Override the device base class"""
        self._time = the_event.time
        if isinstance(the_event, LpdmBuyMaxPowerEvent):
            # A power buyer is informing the GC of the max amount of power it can buy
            # self._logger.debug(
                # self.build_message(
                    # message="buy power max event received {}".format(the_event),
                    # tag="buy_max_power",
                    # value=the_event.value
                # )
            # )
            self.on_buy_max_power_change(the_event)
        elif isinstance(the_event, LpdmBuyPowerPriceEvent):
            # a power buyer is informing the GC of the buy price threshold
            # self._logger.debug(
                # self.build_message(
                    # message="buy power price event received {}".format(the_event),
                    # tag="buy_power_price",
                    # value=the_event.value
                # )
            # )
            self.on_buy_power_price_change(the_event)
        else:
            # divert all other events to the base class
            Device.process_supervisor_event(self, the_event)

    def on_buy_power_price_change(self, the_event):
        """a power buyer has changed its buy price threshold"""
        self._time = the_event.time
        self.power_buyer_manager.set_time(self._time)
        # set the threshold for buying power for a power buyer
        if self.set_buy_price_threshold(the_event.source_device_id, the_event.value):
            self.update_power_purchases()

    def set_buy_price_threshold(self, device_id, value):
        """Set the buy price threshold for a power buyer"""
        device = self.power_buyer_manager.get(device_id)
        if device:
            device.price_threshold = value
            self._logger.debug(self.build_message(
                message="set price threshold for device {}".format(device_id),
                tag="buy_price_threshold",
                value=value
            ))
            return True
        else:
            return False

    def on_buy_max_power_change(self, the_event):
        """a power buyer has changed the max amount of power it can purchase"""
        self._time = the_event.time
        self.power_buyer_manager.set_time(self._time)
        if self.set_buy_max_power(the_event.source_device_id, the_event.value):
            self.update_power_purchases()

    def set_buy_max_power(self, device_id, value):
        """Set the max amount of power a power source can purchase"""
        device = self.power_buyer_manager.get(device_id)
        if device:
            device.capacity = value
            self._logger.debug(self.build_message(
                message="set buy max power for device {}".format(device_id),
                tag="buy_max_power",
                value=value
            ))
            return True
        else:
            return False

    def update_power_purchases(self):
        """Update power purchases"""
        # update the power sources first
        # TODO: check if a power_source_update is needed before doing anything
        # self.power_source_update()
        # calculate how much power is available for selling
        available_power = self.power_source_manager.total_capacity() - self.power_source_manager.total_load()
        if available_power < 1e-7:
            # no power available
            return

        # keep track of all the power buyers to send power change message
        updated_buyers = []
        # go thorugh each power buyer
        for p in self.power_buyer_manager.get_available_power_sources():
            self._logger.debug(self.build_message(
                message="check power source price_thresh-> {}, current_price -> {}".format(p.price_threshold, self._price),
                tag="check_power_source",
                value=0
            ))
            if self._price <= p.price_threshold:
                # price is below the threshold so ok to buy power
                # calculate the max amount of power that can be bought by the device
                max_power = p.capacity - p.load
                if max_power >= 1e-7:
                    # power buy is able to buy more power
                    if max_power > available_power:
                        # not enough available power to buy 100%
                        # purchase what is available
                        power_buy = available_power
                        available_power = 0
                    else:
                        power_buy = max_power
                        available_power -= power_buy

                    self.power_source_manager.add_load(power_buy)
                    if self.power_source_update():
                        # successfully added the load
                        p.set_load(power_buy)
                        updated_buyers.append(p)
                    else:
                        # unable to provide the requested power
                        # TODO: if can't provide power, shutdown ? or restore to previous load?
                        self.power_source_manager.add_load(-1 * power_buy)
                        self.power_source_update()
                        self._logger.debug(self.build_message(
                            message="failed to buy power for device {}".format(p.device_id),
                            tag="buy_power_fail",
                            value=0
                        ))
            else:
                # price is above the threshold
                if p.load > 0:
                    # if power is currently being purchased shut it off
                    self.power_source_manager.remove_load(p.load)
                    self.power_source_update()
                    p.set_load(0.0)
                    updated_buyers.append(p)

        # send messages to the buyer
        for p in updated_buyers:
            self.broadcast_buy_power(p.device_id, p.load)
        self.power_source_manager.reset_changed()

    def broadcast_buy_power(self, target_device_id, value):
        """tell a power buyer how much it can purchase at the moment"""
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast power buy {} to {}".format(value, target_device_id),
                    tag="broadcast_power_buy",
                    value=value
                )
            )
            self._broadcast_callback(LpdmBuyPowerEvent(self._device_id, target_device_id, self._time, value))
        else:
            raise Exception("broadcast_new_power has not been set for this device!")

    def log_end_use_device(self):
        """Log the loads on the connected end-use devices"""
        for d in self.device_manager.devices():
            self._logger.debug(self.build_message(message="load for device {}".format(d.device_id),
                tag="load_{}".format(d.device_id),
                value=d.load
            ))

    def schedule_next_end_use_log_event(self):
        """Schedule the next event for logging the end-use loads"""
        new_event = LpdmEvent(self._time + 60.0 * 5, "log_end_use_device")
        # check if the event is already there
        found_items = filter(lambda d: d.value == "log_end_use_device", self._events)
        if len(found_items) == 0:
            self._events.append(new_event)


    def finish(self):
        """Call finish on the battery also"""
        Device.finish(self)
        if self._battery:
            self._battery.finish()
