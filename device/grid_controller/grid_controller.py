

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
from device.power_source import PowerSource
from device.device import Device
from common.device_class_loader import DeviceClassLoader
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

        self._gc_price = 0.0
        self._total_load = 0.0
        self._total_capacity = 0.0

        # setup the managers for devices and power sources
        self.device_manager = DeviceManager()
        self.power_source_manager = PowerSourceManager()

        # set up class loader
        self._device_class_loader = DeviceClassLoader()

        self._events = []

    def init(self):
        """Initialize the grid controller"""
        self.set_price_logic()

    def set_price_logic(self):
        """Set the logic for calculating the GC's price"""
        # get the class object from the class name
        LogicClass = self._device_class_loader.class_for_name(
            "device.grid_controller.price_logic", self._price_logic_class_name
        )
        # create the object
        self._price_logic = LogicClass(self.power_source_manager)
        self.log_message("Set price logic class to {}".format(LogicClass))

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        """
        Notification from a device that a power change has occurred.
        Could be from either a power source or an eud.
        If from a power source (Diesel Generator, PV, ...) then it's a change in power output.
            This should only happen when a device is turing itself off
        If from an EUD then it's a change in it's power consumption.
        """
        self._time = time

        self.log_message(
            message="Power change, source_device_id = {}, target_device_id = {}".format(source_device_id, target_device_id),
            tag="power",
            value=new_power
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
            p_diff = new_power - device.load
            self.log_message(message="power difference", tag="power_difference", value=p_diff)

            if p_diff == 0:
                # no change in power for the device
                self.log_message(message="No change in power for {}".format(source_device_id))
            elif not self.power_source_manager.has_available_power_sources():
                # power for the device has changed but no available power sources
                # set all devices to zero power
                self.log_message("No power sources available, unable to set load for {}".format(source_device_id))
                for device in self.device_manager.device_list():
                    self.broadcast_new_power(0.0, d.device_id)
            else:
                # power has changed, either positive or negative
                if p_diff > 0:
                    result_success = self.power_source_manager.add_load(p_diff)
                else:
                    result_success = self.power_source_manager.remove_load(p_diff)

                if result_success:
                    # adding/removing load was successfull
                    self.device_manager.set_load(source_device_id, new_power)
                    for p in self.power_source_manager.get_changed_power_sources():
                        # broadcast the messages to the power sources that have changed
                        self.broadcast_new_power(p.load, p.device_id)
                else:
                    # unable to provide the requested power
                    # TODO: if can't provide power, shutdown ? or restore to previous load?
                    self.device_manager.set_load(source_device_id, 0.0)
                    self.broadcast_new_power(0.0, source_device_id)
        # self.schedule_next_events()
        self.calculate_next_ttie()

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        self._time = time
        if not self._static_price:
            self.log_message(
                message="Price change received (new_price = {}, source_device_id = {}, target_device_id = {})".format(new_price, source_device_id, target_device_id),
                tag="price",
                value=new_price
            )
            # set the price for the device
            self.power_source_manager.set_price(source_device_id, new_price)
            self.power_source_manager.optimize_load()
            for p in self.power_source_manager.get_changed_power_sources():
                self.broadcast_new_power(p.load, p.device_id)
            # calculate the new gc price
            if self.calculate_gc_price():
                # send the new price to the devices if changed
                self.send_price_change_to_devices()
            self.power_source_manager.reset_changed()

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time

        self.process_events()
        # self.schedule_next_events()
        self.calculate_next_ttie()
        return

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device registers its capacity to the grid controller it's registered to"""
        self._time = time
        self.log_message(
            message="received capacity change {} -> {}".format(source_device_id, value),
            tag="receive_capacity",
            value=value
        )
        self.power_source_manager.set_capacity(source_device_id, value)
        self.power_source_manager.optimize_load()
        for p in self.power_source_manager.get_changed_power_sources():
            self.broadcast_new_power(p.load, p.device_id)
        self.power_source_manager.reset_changed()

    def add_device(self, new_device_id, DeviceClass):
        "Add a device to the list devices connected to the grid controller"
        if issubclass(DeviceClass, PowerSource):
            self.log_message(message="connected a power source to the gc {} - {}".format(new_device_id, DeviceClass))
            self.power_source_manager.add(new_device_id, DeviceClass)
        else:
            self.log_message(message="connected a device to the gc {} - {}".format(new_device_id, DeviceClass))
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
        # self.log_message("Send price change messages to all devices (t = {0}, p = {1})".format(self._time, self._power_price), logging.INFO)
        self.log_message(
            message="send price change to all devices (new_price = {})".format(self._gc_price),
            tag="send_price_change",
            value="1"
        )
        # send the new price to the non-power-sources
        for d in self.device_manager.devices():
            self.broadcast_new_price(self._gc_price, d.device_id)

    def shutdown(self):
        """Shutdown the grid, set all loads to zero, notify all devices"""
        self.log_message(
            message="Shutdown",
            tag="shutdown",
            value="1"
        )
        self._total_load = 0.0
        # set all device power outputs to zero
        for d in self.device_manager.devices():
            self.broadcast_new_power(0.0, d.device_id)
            d.load = 0.0

        # set the power output of the power sources to zero
        for p in self.power_source_manager.get():
            self.broadcast_new_power(0.0, p.device_id)
            p.load = 0.0


    # def shutdown_generator(self):
        # "Shutdown the generator - shut down all devices, set all loads to 0, notify all connected devices to shutdown"
        # self.log_message(
            # message="Shutdown the generator",
            # tag="shutdown",
            # value="1"
        # )
        # self._total_load = 0.0
        # self._load_on_generator = 0.0
        # self._load_on_battery = 0.0

        # if self._battery and self._battery.is_charging():
            # self._battery.stop_charging()
        # elif self._battery and self._battery.is_discharging():
            # self._battery.stop_discharging()

        # if self._pv and self._load_on_pv > 0:
            # self._load_on_pv = 0.0
            # self._pv.set_power_output(self._time, self._load_on_pv)

        # for item in self._power_usage_by_device:
            # item["power"] = 0.0
            # if item["device_id"] != self.get_diesel_generator_id():
                # self.broadcast_new_power(0.0, item["device_id"])

    # def set_power_for_device(self, source_device_id, power):
        # """
            # Need to keep track of the power output for each device, which is stored in the dictionary self._power_usage_by_device.
            # update or add the new power value, then update the total power output.
        # """
        # found_item = False
        # # Update the existing device if it's already there
        # for item in self._power_usage_by_device:
            # if source_device_id == item["device_id"]:
                # if power != item["power"]:
                    # delta_power = power - item["power"]
                    # self._total_load += delta_power
                    # item["power"] = power
                    # found_item = True
                    # self.log_message("power changed to {}".format(power))
                # break

        # if not found_item:
            # # If the item is not in the list then create a new item for the device
            # self._power_usage_by_device.append({'device_id': source_device_id, 'power': power})
            # self._total_load += power

    def current_output_capacity(self):
        "Current output capacity of the GC (%)"
        return 100.0 * self._total_load / self._capacity

    # def add_load(self, device_id, new_load):
        # """Add load, distrubute power among the various power sources"""
        # # get the available power sources
        # if not self.power_source_manager.has_available_power_sources():
            # raise Exception("There are no available power sources.")

        # if not self.power_source_manager.add_load(new_load):
            # raise Exception

    def set_power_sources(self):
        "Set the power output for the diesel generator, battery, pv, ..."
        # generator_id = self.get_diesel_generator_id()
        output_capacity = self.current_output_capacity()

        previous_load_generator = self._load_on_generator

        if generator_id and self._battery:
            # a generator and battery are connected to the grid controller (and maybe pv)

            # calculate the change in power
            # _total_load will always have the correct value for power needed, the power sources need to be adjusted
            delta_power = self._total_load - self._load_on_battery - self._load_on_generator - self._load_on_pv

            # save the original state of the battery and pv
            previous_load_battery = self._load_on_battery
            previous_load_pv = self._load_on_pv

            self.log_message("set power sources (output_capacity = {}, generator_load = {}, battery_load = {}, battery_soc = {}, total_load = {}, pv = {})".format(
                output_capacity,
                self._load_on_generator,
                self._load_on_battery,
                self._battery.state_of_charge(),
                self._total_load,
                self._load_on_pv), app_log_level=None)

            if self._battery.is_discharging():
                # if battery is discharging
                if self._total_load > 0:
                    if self.current_output_capacity() > 70 and self._battery.state_of_charge() < 0.65:
                        # stop discharging dn do nothing
                        self.battery_neither()
                    elif self._battery.state_of_charge() < 0.20:
                        # stop discharging and start charging
                        self.battery_neither()
                        self.battery_charge()
                else:
                    self.battery_neither()

            elif self._battery.is_charging():
                # battery is charging
                if self._battery.state_of_charge() >= 0.8 or (self.current_output_capacity() < 30 and self._battery.state_of_charge() > 0.65):
                    # stop discharging dn do nothing
                    self.battery_neither()
            else:
                # Neither - not charging and not discharging
                if self._total_load > 0 and self.current_output_capacity() < 30.0 and self._battery.state_of_charge() > 0.65:
                    # start to discharge the battery
                    self.battery_discharge()

            # if there's power output from the pv set it to 0 and add back to the generator
            if self._pv and self._load_on_pv > 0:
                self._load_on_generator += self._load_on_pv
                self._load_on_pv = 0
                self.log_message(
                    message="turn off pv power generation",
                    tag="pv_power",
                    value=0
                )

            # Add the new load to the battery or the generator
            if self._battery.is_discharging() and delta_power:
                self._load_on_battery += delta_power
                if self._load_on_battery > self._battery.capacity():
                    # set the load on the battery to full capacity, add the difference to the generator
                    self._load_on_generator += (self._load_on_battery - self._battery.capacity())
                    self._load_on_battery = self._battery.capacity()
                # log the new battery load if it has changed
                if self._load_on_battery != previous_load_battery:
                    self.log_message(
                        message="load on battery changed",
                        tag="battery_load",
                        value=self._load_on_battery
                    )
            elif delta_power:
                self.log_message("Add the new load ({})to the diesel generator".format(delta_power))
                self._load_on_generator += delta_power

            # take load off of the generator and put it on pv if there's a need
            if self._pv and self._load_on_generator > 0:
                # get the max power available from the pv
                pv_kw_available = self._pv.get_maximum_power(self._time)

                if pv_kw_available > 0 and self._load_on_generator > 0:
                    # there's power available from the pv
                    if pv_kw_available > self._load_on_generator:
                        # pv can take all the generator's load
                        self._load_on_pv = self._load_on_generator
                        self._load_on_generator = 0
                    else:
                        self._load_on_pv = pv_kw_available
                        self._load_on_generator = self._load_on_generator - pv_kw_available

            # update the generator if the required load on it has changed
            if previous_load_generator != self._load_on_generator:
                self.log_message(
                    message="update the load on the generator",
                    tag="generator_load",
                    value=self._load_on_generator
                )
                self.broadcast_new_power(self._load_on_generator, generator_id)


            # update the pv power output if it has changed
            if previous_load_pv != self._load_on_pv:
                self._pv.set_power_output(self._time, self._load_on_pv)
                self.log_message(
                    message="pv power output changed",
                    tag="pv_load",
                    value=self._load_on_pv
                )
                self.log_plot_value("pv_power_output", self._load_on_pv)
        elif generator_id:
            # only a generator is connected to the grid controller
            self.log_message(
                "set power sources (dg = {}, pv = {}, total_load = {})".format(self._load_on_generator, self._load_on_pv, self._total_load)
            )
            previous_load_pv = self._load_on_pv
            self._load_on_generator = self._total_load
            # if previous_load_generator != self._load_on_generator:
                # self.broadcast_new_power(self._total_load, generator_id)
                # self.tug_send_message(action="load_on_generator", is_initial_event=False, value=self._load_on_generator, description="kW")

            # take load off of the generator and put it on pv if there's a need
            if self._pv and self._load_on_generator > 0:
                # get the max power available from the pv
                pv_kw_available = self._pv.get_maximum_power(self._time)
                if pv_kw_available > 0:
                    # there's power available from the pv
                    if pv_kw_available > self._load_on_generator:
                        # pv can take all the generator's load
                        self._load_on_pv = self._load_on_generator
                        self._load_on_generator = 0
                    else:
                        self._load_on_pv = pv_kw_available
                        self._load_on_generator = self._load_on_generator - pv_kw_available

            # update the generator
            if previous_load_generator != self._load_on_generator:
                self.log_message(
                    message="update the load on the generator",
                    tag="generator_load",
                    value=self._load_on_generator
                )
                self.broadcast_new_power(self._load_on_generator, generator_id)

            # update the pv
            if previous_load_pv != self._load_on_pv:
                self.log_message(
                    message="pv power output changed",
                    tag="pv_load",
                    value=self._load_on_pv
                )
                self._pv.set_power_output(self._time, self._load_on_pv)
                self.log_plot_value("pv_power_output", self._load_on_pv)
        else:
            # no power sources are connected to the grid controller
            raise Exception("No power sources are connected to the grid controller")

    def process_events(self):
        "Process any events that need to be processed"

        remove_items = []
        set_power_sources_called = False

        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "battery_status":
                    if not set_power_sources_called:
                        self.set_power_sources()
                        set_power_sources_called = True
                    remove_items.append(event)
                elif event["operation"] == "pv_power_update":
                    if not set_power_sources_called:
                        self.set_power_sources()
                        set_power_sources_called = True
                    remove_items.append(event)
                elif event["operation"] == "emit_initial_price":
                    self.send_price_change_to_devices()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return

    def set_next_battery_update_event(self):
        "If the battery is on update its state of charge every X number of seconds"
        self._events.append({"time": self._time + self._check_battery_soc_rate, "operation": "battery_status"})

    def set_next_pv_update_event(self):
        "Update the pv power output every 15 minutes"
        self._events.append({"time": self._time + self._pv_power_update_rate, "operation": "pv_power_update"})

    # def schedule_next_events(self):
        # "Schedule upcoming events if necessary"
        # if self._battery:
            # # if the battery is charging/discharging then check out the state_of_charge in self._check_battery_soc_rate seconds
            # search_events = [event for event in self._events if event["operation"] == "battery_status"]
            # if not len(search_events):
                # self.set_next_battery_update_event()

        # if self._pv:
            # search_events = [event for event in self._events if event["operation"] == "pv_power_update"]
            # if not len(search_events):
                # self.set_next_pv_update_event()
        # pass

    def set_initial_price_event(self):
        """Let all other devices know of the initial price of energy"""
        self._events.append({"time": 0, "operation": "emit_initial_price"})

    def calculate_next_ttie(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcast_new_ttie(ttie)
