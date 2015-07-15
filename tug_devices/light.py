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
        print("light init")

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

    def adjustHardwarePower(self):
        self.turnOnHardware()

    def turnOnHardware(self):
        # turn on the physical light
        # need to pass it a value from 1-255
        self._hardware_link.on(int((255.0 - 1.0)/(self._max_power_use - 0.0) * self._power_level))
