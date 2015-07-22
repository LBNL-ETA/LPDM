"""
    Implementation of a hue based light
"""
from eud import Eud
from tcplights import TCPLights
from connected_control import ConnectedLight


class Light(Eud):
    def __init__(self, config=None):
        # call the super constructor
        Eud.__init__(self, config)
        self._hardware_link_bridge = TCPLights()

        # Grab one light, since we only have one for the demonstration
        lights = self._hardware_link_bridge.TCPGetLights()
        firstLight = lights.itervalues().next()

        self._hardware_link_light = ConnectedLight(self._hardware_link_bridge, firstLight['did'])
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
