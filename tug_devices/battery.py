"""
    Implementation of a battery
"""

from device import Device
import logging

class Battery(Device):
    """
        Device implementation of a battery.

        The battery is fully controlled by the grid controller, so there's no TTIE calculations;
        and it doesn't respond to any power, price, or time changes.

        Methods:
            startCharging: starts the battery charging,
            stopCharging: stops the battery charging,
            stateOfCharge: gets the current SOC of the battery
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the grid controller

                keys:
                    "device_name" (string): Name of the device
                    "capacity" (float): Capacity of the battery (kWh)
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the battery wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the battery wants to stop charging
                    "max_charge_rate" (float): Max charge rate (Watts)
                    "roundtrip_eff" (float): Fraction of power that is stored and available for withdrawl
        """
        self._device_type = "battery"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "battery"
        self._capacity = float(config["capacity"]) if type(config) is dict and "capacity" in config.keys() else 5.0
        self._current_soc = float(config["current_soc"]) if type(config) is dict and "current_soc" in config.keys() else 1.0
        self._min_soc = float(config["min_soc"]) if type(config) is dict and "min_soc" in config.keys() else 0.2
        self._max_soc = float(config["max_soc"]) if type(config) is dict and "max_soc" in config.keys() else 0.8
        self._max_charge_rate = float(config["max_charge_rate"]) if type(config) is dict and "max_charge_rate" in config.keys() else 1000.0
        self._roundtrip_eff = float(config["roundtrip_eff"]) if type(config) is dict and "roundtrip_eff" in config.keys() else 0.9
        self._min_soc_refresh_rate = 60
        self._battery_on_time = None
        self._last_update_time = None
        self._charge_start_time = None
        self._is_charging = False
        self._is_discharging = False

        # call the super constructor
        Device.__init__(self, config)

    def capacity(self):
        "Return the capcity of the battery (W)"
        return self._capacity * 1000.0

    def onPowerChange(self, time, new_power):
        "Receives messages when a power change has occured"
        return

    def onPriceChange(self, new_price):
        "Receives message when a price change has occured"
        return

    def calculateNextTTIE(self):
        return

    def maxChargeRate(self):
        return self._max_charge_rate

    def chargeRate(self):
        "Charge rate (W)"
        return self._max_charge_rate * self._roundtrip_eff

    def startCharging(self, time):
        self._time = time
        if not self._is_charging:
            self.logMessage("Start charging battery (soc = {})".format(self._current_soc))
            self._is_charging = True
            self._last_update_time = time
        return

    def stopCharging(self, time):
        self._time = time
        if self._is_charging:
            self.logMessage("Stop charging battery (soc = {})".format(self._current_soc))
            self._is_charging = False
            self._last_update_time = time
        return

    def isCharging(self):
        return self._is_charging

    def wantsToStopCharging(self):
        return self._current_soc >= self._max_soc

    def wantsToStartCharging(self):
        return self._current_soc <= self._min_soc

    def discharge(self, amount):
        "Remove energy (kwh) from the battery when requested, battery must be set to discharge first"
        if self._is_discharging:
            self._current_soc = ((self._capacity * self._current_soc) - amount) / self._capacity
            self.tugSendMessage(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")
        else:
            raise Exception("Battery must have been set to discharge before removing energy.")
        return

    def startDischarging(self, time):
        self._time = time
        if not self._is_charging and not self._is_discharging:
            self.logMessage("Start discharging battery (soc = {})".format(self._current_soc))
            self._is_discharging = True
            self._last_update_time = time

    def stopDischarging(self, time):
        self._time = time
        if self._is_discharging:
            self.logMessage("Stop discharging battery (soc = {})".format(self._current_soc))
            self._is_discharging = False
            self._last_update_time = time

    def isDischarging(self):
        return self._is_discharging

    def stateOfCharge(self):
        "Returns the current SOC"
        return self._current_soc

    def updateStateOfCharge(self, time, load_on_battery):
        self._time = time
        if not self._last_update_time or time - self._last_update_time > self._min_soc_refresh_rate:
            if self._is_charging:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) + (self.chargeRate() * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)
                self.tugSendMessage(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")
            elif self._is_discharging and load_on_battery:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) - (load_on_battery * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)
                self.tugSendMessage(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")

            self.logPlotValue("battery_soc", self._current_soc)

            self._last_update_time = time

    # def startUsingBattery(self, time):
    #     if not self.isOn():
    #         self._battery_on_time = time
    #         self.turnOn()

