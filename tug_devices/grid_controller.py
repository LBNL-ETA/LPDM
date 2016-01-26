"""
    Implementation of a Grid Controller
"""

from device import Device
from battery import Battery
from diesel_generator import DieselGenerator
import logging
import colors
import pprint

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
                    "current_fuel_price" (float): Initial price of fuel ($/W-sec)
                    "capacity (float): Maximum available capacity (Watts),
                    "diesel_output_threshold" (float): Percentage of output capacity of the diesel generator to keep above using the battery
                    "check_battery_soc_rate" (int): Rate at which to update the battery state of charge when charging or discharging (seconds)
                    "battery_config" (Dict): Configuration object for the battery attached to the grid controller
        """
        self._device_type = "grid_controller"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "grid_controller"
        self._connected_devices = config["connected_devices"] if type(config) is dict and "connected_devices" in config.keys() else []
        self._current_fuel_price = float(config["current_fuel_price"]) if type(config) is dict and "current_fuel_price" in config.keys() else None
        self._capacity = float(config["capacity"]) if type(config) is dict and "capacity" in config.keys() else 3000.0
        self._diesel_output_threshold = float(config["diesel_output_threshold"]) if type(config) is dict and "diesel_output_threshold" in config.keys() else 70.0
        self._check_battery_soc_rate = int(config["check_battery_soc_rate"]) if type(config) is dict and "check_battery_soc_rate" in config.keys() else 60 * 5

        self._battery = Battery(config["battery_config"]) if type(config) is dict and "battery_config" in config.keys() else None

        self._pv = None

        self._total_load = 0.0
        self._power_usage_by_device = []
        self._load_on_generator = 0.0
        self._load_on_battery = 0.0
        self._load_on_pv = 0.0

        self._diesel_generator_id = None

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

    # def logMessage(self, message, app_log_level=logging.INFO, device_log_level=logging.DEBUG):
        # """Make all grid controller log message purple"""
        # Device.logMessage(self, colors.colorize(message, colors.Colors.PURPLE), app_log_level, device_log_level)

    def getLogMessageString(self, message):
        return colors.colorize(Device.getLogMessageString(self, message), colors.Colors.PURPLE)


    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        self.logMessage("received power change, new power = {}, source_device_id = {}, target_device_id = {}".format(new_power, source_device_id, target_device_id))
        changed_power = False
        if new_power == 0 and source_device_id == self.getDieselGeneratorID() and self._load_on_generator > 0:
            # if the diesel generator has changed its power to zero without being instructed then it's out of fuel
            self.shutdownGenerator()
            changed_power = True
        else:
            changed_power = self.setPowerForDevice(source_device_id, new_power)

        if self._battery:
            self._battery.updateStateOfCharge(self._time, self._load_on_battery)

        self.setPowerSources()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        # self.logMessage("Price change received (t = {0}, p = {1}, source = {2})".format(time, new_price, source_device.deviceName()), logging.INFO)
        self.logMessage("Price change received (new_price = {}, source_device_id = {}, target_device_id = {})".format(new_price, source_device_id, target_device_id), app_log_level=None)
        self._current_fuel_price = new_price
        self._time = time

        # self.setPowerSources()
        # self.scheduleNextEvents()
        # self.calculateNextTTIE()
        self.sendPriceChangeToDevices()

        return

    def onTimeChange(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        if self._battery:
            self._battery.updateStateOfCharge(self._time, self._load_on_battery)
        self.processEvents()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def addDevice(self, new_device_id, type_of_device):
        "Add a device to the list devices connected to the grid controller"
        self.logMessage("added device to the grid controller (device_id = {}, device_type = {})".format(new_device_id, type_of_device))
        self._connected_devices.append({"device_id": new_device_id, "device_type": type_of_device})
        return

    def sendPriceChangeToDevices(self):
        "Sends a change in price notification to the connected devices"
        # self.logMessage("Send price change messages to all devices (t = {0}, p = {1})".format(self._time, self._current_fuel_price), logging.INFO)
        self.logMessage("send price change to all devices (new_price = {})".format(self._current_fuel_price), app_log_level=None)
        for device in self._connected_devices:
            self.broadcastNewPrice(self._current_fuel_price, device["device_id"])
            # device.onPriceChange(self._time, self, self._current_fuel_price)

    def shutdownGenerator(self):
        "Shutdown the generator - shut down all devices, set all loads to 0, notify all connected devices to shutdown"
        self.logMessage("Shutdown the generator")
        self._total_load = 0.0
        self._load_on_generator = 0.0
        self._load_on_battery = 0.0

        if self._battery and self._battery.isCharging():
            self._battery.stopCharging()
        elif self._battery and self._battery.isDischarging():
            self._battery.stopDischarging()

        for item in self._power_usage_by_device:
            item["power"] = 0.0
            if item["device_id"] != self.getDieselGeneratorID():
                self.broadcastNewPower(0.0, item["device_id"])

    def setPowerForDevice(self, source_device_id, power):
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
                break

        if not found_item:
            # If the item is not in the list then create a new item for the device
            self._power_usage_by_device.append({'device_id': source_device_id, 'power': power})
            self._total_load += power
            self.tugSendMessage(action="power_change", is_initial_event=False, value=self._total_load, description="W")

    def currentOutputCapacity(self):
        "Current output capacity of the GC (%)"
        return 100.0 * self._total_load / self._capacity

    def batteryDischarge(self):
        self.logMessage("batteryDischarge (is_charging = {}, is_discharging = {})".format(self._battery.isCharging(), self._battery.isDischarging()), app_log_level=None)
        if self._battery and not self._battery.isCharging() and not self._battery.isDischarging():
            self.logMessage("start battery discharge", app_log_level=None)
            self._battery.startDischarging(self._time)
            if self._load_on_generator > self._battery.capacity():
                self._load_on_generator -= self._battery.capacity()
                self._load_on_battery = self._battery.capacity()
            else:
                self._load_on_battery = self._load_on_generator
                self._load_on_generator = 0.0
        else:
            self.logMessage("battery is not able to discharge, check parameters")
            raise Exception("battery is not able to discharge, check parameters")

    def batteryCharge(self):
        self.logMessage("battery charge (is_charging = {}, is_discharging = {})".format(self._battery.isCharging(), self._battery.isDischarging()), app_log_level=None)
        if self._battery and not self._battery.isCharging() and not self._battery.isDischarging():
            # add the load needed to charge the battery on to the generator
            self._total_load += self._battery.chargeRate()
            self._load_on_generator += self._battery.chargeRate()
        else:
            self.logMessage("battery is not able to charge, check parameters")
            raise Exception("battery is not able to charge, check parameters")

    def batteryNeither(self):
        self.logMessage("battery neither (is_charging = {}, is_discharging = {})".format(self._battery.isCharging(), self._battery.isDischarging()), app_log_level=None)
        if self._battery and self._battery.isDischarging():
            self._battery.stopDischarging(self._time)
            # put the load that was on the battery back on the generator
            self._load_on_generator += self._load_on_battery
            self._load_on_battery = 0.0
        elif self._battery.isCharging():
            self._battery.stopCharging(self._time)
            self._total_load -= self._battery.chargeRate()
            self._load_on_generator -= self._battery.chargeRate()

    def setPowerSources(self):
        "Set the power output for the diesel generator, battery, pv, ..."
        generator_id = self.getDieselGeneratorID()
        output_capacity = self.currentOutputCapacity()

        previous_load_generator = self._load_on_generator

        if generator_id and self._battery:
            # a generator and battery are connected to the grid controller
            delta_power = self._total_load - self._load_on_battery - self._load_on_generator
            previous_load_battery = self._load_on_battery

            self.logMessage("set power sources (output_capacity = {}, generator_load = {}, battery_load = {}, battery_soc = {}, total_load = {})".format(
                output_capacity,
                self._load_on_generator,
                self._load_on_battery,
                self._battery.stateOfCharge(),
                self._total_load), app_log_level=None)

            if self._battery.isDischarging():
                # if battery is discharging
                if self._total_load > 0:
                    if self.currentOutputCapacity() > 70 and self._battery.stateOfCharge() < 0.65:
                        # stop discharging dn do nothing
                        self.batteryNeither()
                    elif self._battery.stateOfCharge() < 0.20:
                        # stop discharging and start charging
                        self.batteryNeither()
                        self.batteryCharge()
                else:
                    self.batteryNeither()

            elif self._battery.isCharging():
                # battery is charging
                if self._battery.stateOfCharge() >= 0.8 or (self.currentOutputCapacity() < 30 and self._battery.stateOfCharge() > 0.65):
                    # stop discharging dn do nothing
                    self.batteryNeither()
            else:
                # Neither - not charging and not discharging
                if self._total_load > 0 and self.currentOutputCapacity() < 30.0 and self._battery.stateOfCharge() > 0.65:
                    # start to discharge the battery
                    self.tugSendMessage(action="battery_discharge", is_initial_event=False, value=1, description="")
                    self.logMessage("start discharging the battery")
                    self.batteryDischarge()

            # Add the new load to the battery or the generator
            if self._battery.isDischarging() and delta_power:
                self.logMessage("Add the new load ({})to the battery".format(delta_power))
                self._load_on_battery += delta_power
                if self._load_on_battery > self._battery.capacity():
                    self._load_on_generator += (self._load_on_battery - self._battery.capacity())
                    self._load_on_battery = self._battery.capacity()
            elif delta_power:
                self.logMessage("Add the new load ({})to the diesel generator".format(delta_power))
                self._load_on_generator += delta_power

            # update the generator
            if previous_load_generator != self._load_on_generator:
                self.broadcastNewPower(self._load_on_generator, generator_id)

            if previous_load_generator != self._load_on_generator or previous_load_battery != self._load_on_battery:
                self.tugSendMessage(action="gc_total_load", is_initial_event=False, value=self._total_load, description="W")
                self.tugSendMessage(action="gc_load_on_generator", is_initial_event=False, value=self._load_on_generator, description="W")
                self.tugSendMessage(action="gc_load_on_battery", is_initial_event=False, value=self._load_on_battery, description="W")
                self.tugSendMessage(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")
                self.tugSendMessage(action="battery_is_charging", is_initial_event=False, value=self._battery.isCharging(), description="")
                self.tugSendMessage(action="battery_is_discharging", is_initial_event=False, value=self._battery.isDischarging(), description="")
                # self.tugSendMessage(action="battery_wants_to_discharge", is_initial_event=False, value=self._battery.stateOfCharge, description="")
                self.tugSendMessage(action="battery_soc", is_initial_event=False, value=self._battery.stateOfCharge(), description="")

        elif generator_id:
            # only a generator is connected to the grid controller
            self.logMessage("set power sources (generator)", app_log_level=None)
            self._load_on_generator = self._total_load
            if previous_load_generator != self._load_on_generator:
                self.broadcastNewPower(self._total_load, generator_id)
                self.tugSendMessage(action="load_on_generator", is_initial_event=False, value=self._load_on_generator, description="kW")
            self.tugSendMessage(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")
            # print("generator output = {0}".format(generator.currentOutputCapacity()))
        else:
            # no power sources are connected to the grid controller
            raise Exception("No power sources are connected to the grid controller")

    def getDieselGeneratorID(self):
        "Find the diesel generator in the connected devices"
        if self._diesel_generator_id:
            return self._diesel_generator_id
        else:
            generator_id = None
            for device in self._connected_devices:
                if device["device_type"] is DieselGenerator:
                    generator_id = device["device_id"]
                    self._diesel_generator_id = generator_id
                    break

            return generator_id


    def connectedDevices(self):
        return self._connected_devices

    def processEvents(self):
        "Process any events that need to be processed"

        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "battery_status":
                    self.tugSendMessage(action="event_battery_status", is_initial_event=True, value="", description="")
                    self.logMessage("received battery status event", app_log_level=None)
                    self.logMessage(pprint.pformat(event), app_log_level=None)
                    self.setPowerSources()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return

    def setNextBatteryUpdateEvent(self):
        "If the battery is on update its state of charge every X number of seconds"
        self._events.append({"time": self._time + self._check_battery_soc_rate, "operation": "battery_status"})

    def scheduleNextEvents(self):
        "Schedule upcoming events if necessary"
        if self._battery:
            # if the battery is charging/discharging then check out the state_of_charge in self._check_battery_soc_rate seconds
            search_events = [event for event in self._events if event["operation"] == "battery_status"]
            if not len(search_events):
                self.setNextBatteryUpdateEvent()
        return

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcastNewTTIE(ttie)
