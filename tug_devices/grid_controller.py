"""
    Implementation of a Grid Controller
"""

from device import Device
from battery import Battery
from diesel_generator import DieselGenerator
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
                    "current_fuel_price" (float): Initial price of fuel ($/W-sec)
                    "capacity (float): Maximum available capacity (Watts),
                    "diesel_output_threshold" (float): Percentage of output capacity of the diesel generator to keep above using the battery
                    "check_battery_soc_rate" (int): Rate at which to update the battery state of charge when charging or discharging (seconds)
                    "battery_config" (Dict): Configuration object for the battery attached to the grid controller
        """
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "grid_controller"
        self._connected_devices = config["connected_devices"] if type(config) is dict and "connected_devices" in config.keys() else []
        self._current_fuel_price = config["current_fuel_price"] if type(config) is dict and "current_fuel_price" in config.keys() else None
        self._capacity = config["capacity"] if type(config) is dict and "capacity" in config.keys() else 3000.0
        self._diesel_output_threshold = config["diesel_output_threshold"] if type(config) is dict and "diesel_output_threshold" in config.keys() else 70.0
        self._check_battery_soc_rate = config["check_battery_soc_rate"] if type(config) is dict and "check_battery_soc_rate" in config.keys() else 60 * 5
        self._battery = Battery(config["batter_config"] if type(config) is dict and "batter_config" in config.keys() else {})
        self._pv = None

        self._total_load = 0.0
        self._power_usage_by_device = []
        self._load_on_generator = 0.0
        self._load_on_battery = 0.0
        self._load_on_pv = 0.0

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        # self.logMessage("Power change received (t = {0}, p = {1}, source = {2})".format(time, new_power, source_device.deviceName()), logging.INFO)
        self._time = time
        self.setPowerForDevice(source_device_id, new_power)
        self._battery.updateStateOfCharge(self._time)
        self.setPowerSources()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        # self.logMessage("Price change received (t = {0}, p = {1}, source = {2})".format(time, new_price, source_device.deviceName()), logging.INFO)
        self._current_fuel_price = new_price
        self._time = time

        self.sendPriceChangeToDevices()

        return

    def onTimeChange(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self._battery.updateStateOfCharge(self._time)
        self.processEvents()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def addDevice(self, new_device_id, type_of_device):
        "Add a device to the list devices connected to the grid controller"
        self._connected_devices.append({"device_id": new_device_id, "device_type": type_of_device})
        return

    def sendPriceChangeToDevices(self):
        "Sends a change in price notification to the connected devices"
        # self.logMessage("Send price change messages to all devices (t = {0}, p = {1})".format(self._time, self._current_fuel_price), logging.INFO)
        for device in self._connected_devices:
            self.broadcastNewPrice(self._current_fuel_price, device["device_id"])
            # device.onPriceChange(self._time, self, self._current_fuel_price)

    def setPowerForDevice(self, source_device_id, power):
        """
            Need to keep track of the power output for each device, which is stored in the dictionary self._power_usage_by_device.
            update or add the new power value, then update the total power output.
        """
        found_item = False
        # Update the existing device if it's already there
        for item in self._power_usage_by_device:
            if source_device_id == item["device_id"]:
                delta_power = power - item["power"]
                self._total_load += delta_power
                item["power"] = power
                found_item = True
                break

        if not found_item:
            # If the item is not in the list then create a new item for the device
            self._power_usage_by_device.append({'device_id': source_device_id, 'power': power})
            self._total_load += power

        self.tugLogAction(action="power_change", is_initial_event=False, value=self._total_load, description="W")
        return

    def currentOutputCapacity(self):
        "Current output capacity of the GC (%)"
        return 100.0 * self._total_load / self._capacity

    def setPowerSources(self):
        "Set the power output for the diesel generator, battery, pv, ..."
        generator_id = self.getDieselGenerator()
        output_capacity = self.currentOutputCapacity()

        if generator_id and self._battery:
            if self._battery.isCharging() and self._battery.wantsToStopCharging():
                # Stop charging, take the load needed to charge the battery off of the generator
                self.tugLogAction(action="battery_charge", is_initial_event=False, value=0, description="")
                self._battery.stopCharging(self._time)
                self._total_load -= self._battery.chargeRate()
                self._load_on_generator -= self._battery.chargeRate()
                self.broadcastNewPower(self._load_on_generator, generator_id)

            elif self._battery.isDischarging() and self._battery.wantsToStartCharging():
                # Start charging the battery, add the load back on to the generator
                self.tugLogAction(action="battery_charge", is_initial_event=False, value=1, description="")
                self._battery.stopDischarging(self._time)
                self._battery.startCharging(self._time)

                # put the load that was on the battery back on the generator
                self._load_on_generator += self._load_on_battery
                self._load_on_battery = 0.0

                # add the load needed to charge the battery on to the generator
                self._total_load += self._battery.chargeRate()
                self._load_on_generator += self._battery.chargeRate()
                self.broadcastNewPower(self._load_on_generator, generator_id)

            elif self._load_on_generator and not self._battery.isDischarging() and not self._battery.isCharging() and output_capacity < 30.0 and self._battery.stateOfCharge() > 0.65:
                # use all battery if output capacity of generator < 30% and battery >= 65% charged
                self.tugLogAction(action="battery_discharge", is_initial_event=False, value=1, description="")
                self._load_on_generator = 0.0    
                self._load_on_battery = self._total_load
                
                self.broadcastNewPower(0.0, generator_id)
                self._battery.startDischarging(self._time)
            else:
                # self.tugLogAction(action="else", is_initial_event=False, value=, description="")

                delta_power = self._total_load - self._load_on_battery + self._load_on_generator

                if delta_power:
                    if not self._battery.isDischarging() and not self._battery.isCharging():
                        self._battery.startDischarging(self._time)
                    
                    if self._battery.isDischarging():    
                        self._load_on_battery += delta_power
                        if self._load_on_battery > self._battery.capacity():
                            self._load_on_generator += (self._load_on_battery - self._battery.capacity())
                            self._load_on_battery = self._battery.capacity()
                    else:
                        self._load_on_generator += delta_power

                    self.broadcastNewPower(self._load_on_generator, generator_id)



            self.tugLogAction(action="gc_total_load", is_initial_event=False, value=self._total_load, description="W")
            self.tugLogAction(action="gc_load_on_generator", is_initial_event=False, value=self._load_on_generator, description="W")
            self.tugLogAction(action="gc_load_on_battery", is_initial_event=False, value=self._load_on_battery, description="W")
            self.tugLogAction(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")
            self.tugLogAction(action="battery_soc", is_initial_event=False, value=self._battery.stateOfCharge(), description="")

        elif generator_id:
            self._load_on_generator = self._total_load
            # generator.onPowerChange(self._time, self, self._total_load)
            self.broadcastNewPower(self._total_load, generator_id)
            self.tugLogAction(action="load_on_generator", is_initial_event=False, value=self._load_on_generator, description="kW")
            self.tugLogAction(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")
            # print("generator output = {0}".format(generator.currentOutputCapacity()))
        else:
            raise Exception("No power sources are connected to the grid controller")

    def getDieselGenerator(self):
        "Find the diesel generator in the connected devices"
        generator_id = None
        for device in self._connected_devices:
            if device["device_type"] is DieselGenerator:
                generator_id = device["device_id"]
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
        if self._battery and (self._battery.isCharging() or self._battery.isDischarging()):
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
            self.broadcastNewTTIE(ttie)
            self._ttie = ttie
