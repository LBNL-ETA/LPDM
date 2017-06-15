from device.base.eud import Eud
import logging

class Light(Eud):
    def __init__(self, config = None):
        # call the super constructor
        Eud.__init__(self, config)

        self._device_type = "light"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "Light")
