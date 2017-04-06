

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
    Implementation of a laptop attached to a Wemo Insight switch
"""

from insight_eud import InsightEud
from laptop_power_control.remote_laptop_control import RemoteLaptopControl


class Laptop(InsightEud):
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
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the laptop wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the laptop wants to stop charging
                    "min_soc_refresh_rate" (int) rate at which soc will be refreshed
                    "ipaddr" (string) address at which laptop is currently located
                    "insight_server_url" (string) address at which wemo insight is currently located
                    "insight_name" (string) device id of wemo insight
                    "current_plan" (int) integer representing the current power plan
        """

        self._current_soc = config["current_soc"] if type(config) is dict and "current_soc" in config.keys() else 1.0
        self._min_soc = config["min_soc"] if type(config) is dict and "min_soc" in config.keys() else 0.2
        self._max_soc = config["max_soc"] if type(config) is dict and "max_soc" in config.keys() else 0.8
        self._last_update_time = None
        self._min_soc_refresh_rate = 60
        # No laptop is set up, so IP is a dummy for now.
        self._insight_server_url = config['insight_server_url'] if type(config) is dict and 'insight_ipaddr' in config.keys() else None
        self._insight_name = config['insight_name'] if type(config) is dict and 'insight_name' in config.keys() else 'WeMo Insight'
        self._laptop_link = RemoteLaptopControl(self.ipaddr)
        self._current_plan = self._laptop_link.getPlan()
        self._current_soc = self._laptop_link.getSoc()

        # call the super constructor
        InsightEud.__init__(self, config)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        InsightEud.onPowerChange(self, source_device_id, target_device_id, time, new_power)
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        InsightEud.onPriceChange(self, source_device_id, target_device_id, time, new_price)
        return

    def isCharging(self):
        return self._current_soc > 100

    def stateOfCharge(self):
        "Returns the current SOC"
        return self._current_soc

    def setPowerLevel(self):
        "Set the power level of the Laptop"
        InsightEud.setPowerLevel(self)
        soc = self._laptop_link.getSoc()
        if soc < 20:
            self.turnOn(self._time)
        elif self._price > 40:
            self.turnOff(self._time)
        else:
            self.turnOn(self._time)

    def updateStateOfCharge(self, time, load_on_laptop):
        "Updates state of charge and logs to tug logger"
        self._time = time
        self._current_soc = self._laptop_link.getSoc()
        if not self._last_update_time or time - self._last_update_time > self._min_soc_refresh_rate:
            if self._current_soc > 100:
                self._current_soc = self._laptop_link.getSoc()
                self.tugSendMessage(action="state_of_charge", is_initial_event=False, value=self._current_soc, description="")
            self._last_update_time = time
