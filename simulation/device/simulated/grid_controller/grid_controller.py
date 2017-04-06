

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
from device.base.power_source import PowerSource
from device.base.device import Device
from device.simulated.battery import Battery
from common.device_class_loader import DeviceClassLoader
from device.scheduler import LpdmEvent
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

        # setup the logic for calculating the gc's price, default to average price
        self._price_logic_class_name = config.get("price_logic_class", "AveragePriceLogic")
        self._price_logic = None

        # setup the battery if requested
        self._battery = None
        self.battery_config = config.get("battery", None)

        self._gc_price = 0.0
        self._total_load = 0.0

        # setup the managers for devices and power sources
        self.device_manager = DeviceManager()
        self.power_source_manager = PowerSourceManager()

        # set up class loader
        self._device_class_loader = DeviceClassLoader()

    def init(self):
        """Initialize the grid controller"""
        self.power_source_manager.set_time(self._time)
        self.set_price_logic()
        self.init_battery()
        self.calculate_next_ttie()

    def init_battery(self):
        """Setup the battery"""
        if not self.battery_config is None:
            # initialize the battery
            self._battery = Battery(self.battery_config)
            # add it to the power source manager, set its price and capacity
            self.power_source_manager.add(self._battery._device_id, Battery, self._battery)
            self.power_source_manager.set_capacity(self._battery._device_id, self._battery._capacity)
            self.power_source_manager.set_price(self._battery._device_id, self._battery._price)
            # setup the shared objects for events and power sources
            self._battery.set_event_list(self._events)
            self._battery.set_power_source_manager(self.power_source_manager)
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

        self._logger.debug(
            self.build_message(
                message="Power change, source_device_id = {}, new_power = {}".format(source_device_id, new_power),
                tag="receive_power",
                value=new_power
            )
        )

        # is this a power source or an eud?
        if self.power_source_manager.get(source_device_id):
            # if it's a power source, register its new usage
            # TODO: check capacity?
            self.power_source_manager.set_load(source_device_id, new_power)
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
                self._logger.debug(self.build_message(message="old load = {}, new load = {}, p_diff = {}".format(device.load, new_power, p_diff)))
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

        self.power_source_manager.reset_changed()
        # self.schedule_next_events()
        self.calculate_next_ttie()

    def power_source_update(self):
        """Update the power source manager."""
        result_success = self.power_source_manager.optimize_load()
        if not result_success and self._battery and self._battery._is_charging:
            # if can't add the load and the battery is charging, stop charging and try again
            self._battery.stop_charging()
            result_success = self.power_source_manager.optimize_load()

        if result_success:
            # check if the battery needs to be charged, charge if available
            if self._battery and self._battery._can_charge and not self._battery._is_charging:
                if self.power_source_manager.can_handle_load(self._battery.charge_rate()):
                    self._battery.start_charging()
                    result_success = self.power_source_manager.optimize_load()
                    if not result_success:
                        self._logger.error(self.build_message("Unable to charge battery."))
                        self.stop_charging()
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

        self.process_events()
        self.schedule_next_events()
        self.calculate_next_ttie()
        self.power_source_manager.reset_changed()
        return

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device registers its capacity to the grid controller it's registered to"""
        self._time = time
        self.power_source_manager.set_time(self._time)
        self._logger.debug(
            self.build_message(
                message="received capacity change {} -> {}".format(source_device_id, value),
                tag="receive_capacity",
                value=value
            )
        )
        self.power_source_manager.set_capacity(source_device_id, value)
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

    def add_device(self, new_device_id, DeviceClass):
        "Add a device to the list devices connected to the grid controller"
        if issubclass(DeviceClass, PowerSource):
            self._logger.info(
                self.build_message(message="connected a power source to the gc {} - {}".format(new_device_id, DeviceClass))
            )
            self.power_source_manager.add(new_device_id, DeviceClass)
        else:
            self._logger.info(
                self.build_message(message="connected a device to the gc {} - {}".format(new_device_id, DeviceClass))
            )
            self.device_manager.add(new_device_id, DeviceClass)

    def calculate_gc_price(self):
        """Calculate the price grid controller's price"""
        price_has_changed = False
        previous_price = self._gc_price
        self._gc_price = self._price_logic.get_price()
        # return boolean indicating if price has changed
        return previous_price != self._gc_price

    def send_price_change_to_devices(self):
        "Sends a change in price notification to the connected devices"
        self._logger.debug(
            self.build_message(
                message="send price change to all devices (new_price = {})".format(self._gc_price),
                tag="send_price_change",
                value="1"
            )
        )
        # send the new price to the non-power-sources
        for d in self.device_manager.devices():
            self.broadcast_new_price(self._gc_price, d.device_id)

    def shutdown(self):
        """Shutdown the grid, set all loads to zero, notify all devices"""
        self._logger.info(
            self.build_message(
                message="Shutdown",
                tag="shutdown",
                value="1"
            )
        )
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

        remove_items = []
        set_power_sources_called = False

        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "emit_initial_price":
                    self.send_price_change_to_devices()
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
        if self._battery:
            # the battery shares the same event array as the gc
            self._battery.schedule_next_events()

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

    def finish(self):
        """Call finish on the battery also"""
        Device.finish(self)
        if self._battery:
            self._battery.finish()
