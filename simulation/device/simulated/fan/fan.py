from device.base.eud import Eud
import logging

class Fan(Eud):
    def __init__(self, config = None):
        # call the super constructor
        Eud.__init__(self, config)

        self._device_type = "fan"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "Fan")

