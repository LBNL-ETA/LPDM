

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
    Implementation of a hue based light
"""
from eud import Eud
from hue_control import HueBridge
from hue_light import HueLight

class Light(Eud):
    def __init__(self, config = None):
        # call the super constructor
        Eud.__init__(self, config)
        self._hardware_link_bridge = HueBridge()
        self._hardware_link_light  = HueLight(self._hardware_link_bridge, '1')
        print("light init")

    def turnOn(self):
        "Turn on the device - Override the base class method to add the functionality to interact with the light hardware"
        print('*** light turn on ***')

        Eud.turnOn(self)

        # turn on the physical light
        # need to pass it a value from 1-255
        self._hardware_link_light.on(int((255.0 - 1.0)/(100.0 - 0.0) * self._power_level))

    def turnOff(self):
        "Turn on the device - Override the base class method to add the functionality to interact with the light hardware"
        print('*** light turn off ***')
        # if self._power_level and self._in_operation:
        Eud.turnOff(self)

            # turn on the physical light
            # need to pass it a value from 1-255
        self._hardware_link_light.off()
