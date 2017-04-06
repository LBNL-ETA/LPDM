

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
    Implementation of a  WEMO based light
"""
from eud import Eud
from wemo_control.wemo_light import WemoLight

class Light(Eud):
    def __init__(self, config = None):
        # call the super constructor
        Eud.__init__(self, config)
        self._hardware_link = WemoLight('Lightbulb 01')
        self.current_light_power = 0

    def turnOn(self):
        "Turn on the device - Override the base class method to add the functionality to interact with the light hardware"
        print('*** light turn on ***')

        Eud.turnOn(self)

        self.turnOnHardware()

    def turnOff(self):
        "Turn on the device - Override the base class method to add the functionality to interact with the light hardware"
        print('*** light turn off ***')
        # if self._power_level and self._in_operation:
        Eud.turnOff(self)

        self._hardware_link.off()
        self.current_light_power = 0

    def adjustHardwarePower(self):
        self.turnOnHardware()

    def turnOnHardware(self):
        # turn on the physical light
        # need to pass it a value from 1-255
        new_light_power = int((255.0 - 1.0)/(self._max_power_use - 0.0) * self._power_level)
        if new_light_power and (not self.current_light_power or abs(new_light_power - self.current_light_power) >= 15):
            print('update light power {0}'.format(new_light_power))
            self._hardware_link.on(new_light_power)
            self.current_light_power = new_light_power
