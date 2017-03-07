

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

from device.device import Device
from device.battery import Battery
from device.pv import Pv
from device.diesel_generator import DieselGenerator
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
                "connected_devices (List): Array of devices connected to the grid controller,
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
        self._connected_devices = config.get("connected_devices", [])
        self._power_price = config.get("power_price", None)
        self._capacity = config.get("capacity", 3000.0)
        self._check_battery_soc_rate = config.get("check_battery_soc_rate", 300)
        self._pv_power_update_rate = config.get("pv_power_update_rate", 900)

        self._battery = Battery(config["battery_config"]) if type(config) is dict and "battery_config" in config.keys() else None
        self._pv = Pv(config["pv_config"]) if type(config) is dict and "pv_config" in config.keys() and config["pv_config"] else None

        self._total_load = 0.0
        self._power_usage_by_device = []
        self._load_on_generator = 0.0
        self._load_on_battery = 0.0
        self._load_on_pv = 0.0

        self._diesel_generator_id = None

        self._events = []

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        self.log_message(
            message="Power change, source_device_id = {}, target_device_id = {}".format(source_device_id, target_device_id),
            tag="power",
            value=new_power
        )

        changed_power = False
        if new_power == 0 and source_device_id == self.get_diesel_generator_id() and self._load_on_generator > 0:
            # if the diesel generator has changed its power to zero without being instructed then it's out of fuel
            self.shutdown_generator()
            changed_power = True
        else:
            changed_power = self.set_power_for_device(source_device_id, new_power)

        if self._battery:
            self._battery.update_state_of_charge(self._time, self._load_on_battery)

        self.set_power_sources()
        self.schedule_next_events()
        self.calculate_next_ttie()
        return

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self.log_message(
                message="Price change received (new_price = {}, source_device_id = {}, target_device_id = {})".format(new_price, source_device_id, target_device_id),
                tag="price",
                value=new_price
            )
            self._power_price = new_price
            self._time = time

            self.send_price_change_to_devices()
        return

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        if self._battery:
            self._battery.update_state_of_charge(self._time, self._load_on_battery)
        self.process_events()
        self.schedule_next_events()
        self.calculate_next_ttie()
        return

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device registers its capacity to the grid controller it's registered to"""
        self.log_message(
            message="received capacity change {} -> {}".format(source_device_id, value)
        )

    def add_device(self, new_device_id, type_of_device):
        "Add a device to the list devices connected to the grid controller"
        self.log_message(
            "added device to the grid controller (device_id = {}, device_type = {})".format(new_device_id, type_of_device)
        )
        self._connected_devices.append({"device_id": new_device_id, "device_type": type_of_device})
        return

    def send_price_change_to_devices(self):
        "Sends a change in price notification to the connected devices"
        # self.log_message("Send price change messages to all devices (t = {0}, p = {1})".format(self._time, self._power_price), logging.INFO)
        self.log_message(
            message="send price change to all devices (new_price = {})".format(self._power_price),
            tag="send_price_change",
            value="1"
        )
        for device in self._connected_devices:
            self.broadcast_new_price(self._power_price, device["device_id"])

    def shutdown_generator(self):
        "Shutdown the generator - shut down all devices, set all loads to 0, notify all connected devices to shutdown"
        self.log_message(
            message="Shutdown the generator",
            tag="shutdown",
            value="1"
        )
        self._total_load = 0.0
        self._load_on_generator = 0.0
        self._load_on_battery = 0.0

        if self._battery and self._battery.is_charging():
            self._battery.stop_charging()
        elif self._battery and self._battery.is_discharging():
            self._battery.stop_discharging()

        if self._pv and self._load_on_pv > 0:
            self._load_on_pv = 0.0
            self._pv.set_power_output(self._time, self._load_on_pv)

        for item in self._power_usage_by_device:
            item["power"] = 0.0
            if item["device_id"] != self.get_diesel_generator_id():
                self.broadcast_new_power(0.0, item["device_id"])

    def set_power_for_device(self, source_device_id, power):
        """
            Need to keep track of the power output for each device, which is stored in the dictionary self._power_usage_by_device.
            update or add the new power value, then update the total power output.
        """
        found_item = False
        # Update the existing device if it's already there
        for item in self._power_usage_by_device:
            if source_device_id == item["device_id"]:
                if power != item["power"]:
                    delta_power = power - item["power"]
                    self._total_load += delta_power
                    item["power"] = power
                    found_item = True
                    self.log_message("power changed to {}".format(power))
                break

        if not found_item:
            # If the item is not in the list then create a new item for the device
            self._power_usage_by_device.append({'device_id': source_device_id, 'power': power})
            self._total_load += power

    def current_output_capacity(self):
        "Current output capacity of the GC (%)"
        return 100.0 * self._total_load / self._capacity

    def battery_discharge(self):
        if self._battery and not self._battery.is_charging() and not self._battery.is_discharging():
            self.log_message(
                message="start battery discharge",
                tag="battery_discharge",
                value="1"
            )
            self._battery.start_discharging(self._time)
            if self._load_on_generator > self._battery.capacity():
                self._load_on_generator -= self._battery.capacity()
                self._load_on_battery = self._battery.capacity()
            else:
                self._load_on_battery = self._load_on_generator
                self._load_on_generator = 0.0

            self.log_message(
                message="load_on_battery",
                tag="load_battery",
                value=self._load_on_battery
            )
            self.log_message(
                message="load_on_generator",
                tag="load_generator",
                value=self._load_on_generator
            )
        else:
            self.log_message("battery is not able to discharge, check parameters")
            raise Exception("battery is not able to discharge, check parameters")

    def battery_charge(self):
        if self._battery and not self._battery.is_charging() and not self._battery.is_discharging():
            # add the load needed to charge the battery on to the generator
            self._total_load += self._battery.charge_rate()
            self._load_on_generator += self._battery.charge_rate()
            self.log_message(
                message="charge the battery",
                tag="battery_charge",
                value=self.battery.charge_rate()
            )
        else:
            self.log_message("battery is not able to charge, check parameters")
            raise Exception("battery is not able to charge, check parameters")

    def battery_neither(self):
        self.log_message("battery neither (is_charging = {}, is_discharging = {})".format(self._battery.is_charging(), self._battery.is_discharging()), app_log_level=None)
        if self._battery and self._battery.is_discharging():
            self._battery.stop_discharging(self._time)
            # put the load that was on the battery back on the generator
            self._load_on_generator += self._load_on_battery
            self._load_on_battery = 0.0
            self.log_message(
                message="stop battery discharge",
                tag="battery_discharge",
                value=0
            )
        elif self._battery.is_charging():
            self._battery.stop_charging(self._time)
            self._total_load -= self._battery.charge_rate()
            self._load_on_generator -= self._battery.charge_rate()
            self.log_message(
                message="stop charging the battery",
                tag="battery_charge",
                value=0
            )

    def set_power_sources(self):
        "Set the power output for the diesel generator, battery, pv, ..."
        generator_id = self.get_diesel_generator_id()
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

    def get_diesel_generator_id(self):
        "Find the diesel generator in the connected devices"
        if self._diesel_generator_id:
            return self._diesel_generator_id
        else:
            generator_id = None
            for device in self._connected_devices:
                if device["device_type"] == "diesel_generator":
                    generator_id = device["device_id"]
                    self._diesel_generator_id = generator_id
                    break

            return generator_id


    def connected_devices(self):
        return self._connected_devices

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

    def schedule_next_events(self):
        "Schedule upcoming events if necessary"
        if self._battery:
            # if the battery is charging/discharging then check out the state_of_charge in self._check_battery_soc_rate seconds
            search_events = [event for event in self._events if event["operation"] == "battery_status"]
            if not len(search_events):
                self.set_next_battery_update_event()

        if self._pv:
            search_events = [event for event in self._events if event["operation"] == "pv_power_update"]
            if not len(search_events):
                self.set_next_pv_update_event()

        return

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
