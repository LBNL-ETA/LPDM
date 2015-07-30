"""
    Implementation of a laptop using hardware adapter
"""

from device import Device
import logging
from laptop_power_control.remote_laptop_control import RemoteLaptopControl

class Laptop(Device):
    """
        Device implementation of a laptop.

        Methods:
            startCharging: starts the laptop charging,
            stopCharging: stops the laptop charging,
            stateOfCharge: gets the current SOC of the laptop
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the grid controller

                keys:
                    "device_name" (string): Name of the device
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the laptop wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the laptop wants to stop charging
                    "roundtrip_eff" (float): Fraction of power that is stored and available for withdrawl
                    "ipaddr" (string) address at which laptop is currently located.
        """
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "laptop"
        self._current_soc = config["current_soc"] if type(config) is dict and "current_soc" in config.keys() else 1.0
        self._min_soc = config["min_soc"] if type(config) is dict and "min_soc" in config.keys() else 0.2
        self._max_soc = config["max_soc"] if type(config) is dict and "max_soc" in config.keys() else 0.8
        self._roundtrip_eff = config["roundtrip_eff"] if type(config) is dict and "roundtrip_eff" in config.keys() else 0.9
        self._min_soc_refresh_rate = 60
        self._last_update_time = None
        self._charge_start_time = None
        self._is_charging = False
        # No laptop is set up, so IP is a dummy for now.
        self._ipaddr = config['ipaddr'] if type(config) is dict and 'ipaddr' in config.keys() else '192.168.1.20'
        self._laptop_link = RemoteLaptopControl('self.ipaddr')

        # call the super constructor
        Device.__init__(self, config)

    def onPowerChange(self, time, new_power):
        "Receives messages when a power change has occured"
        return

    def onPriceChange(self, new_price):
        "Receives message when a price change has occured"
        return

    def calculateNextTTIE(self):
        return
   
    def startCharging(self, time):
        self._time = time
        if not self._is_charging:
            self._is_charging = True
            self._last_update_time = time
        return

    def stopCharging(self, time):
        self._time = time
        if self._is_charging:
            self._is_charging = False
            self._last_update_time = time
        return

    def isCharging(self):
        return self._current_soc == 111

    def wantsToStopCharging(self):
        return self._current_soc >= self._max_soc

    def wantsToStartCharging(self):
        return self._current_soc <= self._min_soc

    def stateOfCharge(self):
        "Returns the current SOC"
        return self._current_soc

    def updateStateOfCharge(self, time, load_on_laptop):
        self._time = time
        if not self._last_update_time or time - self._last_update_time > self._min_soc_refresh_rate:
            if self._is_charging:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) + (self.chargeRate() * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)
                self.tugLogAction(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")
            elif self._is_discharging and load_on_laptop:
                self._current_soc = ((self._capacity * 1000.0 * self._current_soc) - (load_on_laptop * (time - self._last_update_time) / 3600.0)) / (self._capacity * 1000.0)
                self.tugLogAction(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")

            self._last_update_time = time
