

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
Implementation of a PWM and beaglebone based EUD device.
"""

from eud import Eud
from variable_speed_fan_control.fan_control import PWMfan
import logging

class PWMfan_eud(Eud, PWMfan):
    def __init__(self, config = None):
        self._device_type = "pwm_fan"

        # Call super constructor
        Eud.__init__(self, config)

        # Server on which WeMo connections are running
        self._login_at_ip  = config["login_at_ip"] if type(config) is dict and "login_at_ip" in config.keys() else None
        self._fan_speed    = config["fan_speed"] if type(config) is dict and "fan_speed" in config.keys() else 100

        self._fan_max = 99
        self._fan_min = 1
        self._current_fan_speed = None

        # Call insight drivers constructor
        PWMfan.__init__(self, self._login_at_ip)

    # Override for specific device
    def turnOff(self):
        "Turns pwm duty cycle to 0% duty cycle"
        # Please not, 0% does NOT turn off the fan. Fan can only be turned off by removing power.
        # call super
        Eud.turnOff(self)
        self.set_fan_speed(str(self._fan_min))

    def adjustHardwarePower(self):
        # Set the power level for the fan, only change if difference > 5
        new_fan_speed = int(float(self._power_level) / self._max_power_use * 100)
        if not self._current_fan_speed or (abs(self._current_fan_speed - new_fan_speed) > 5):
            self.set_fan_speed(str(new_fan_speed))
            self._current_fan_speed = new_fan_speed
