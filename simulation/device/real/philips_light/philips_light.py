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


import os

with open("/tmp/LPDM_light_pythonpath", "a") as f:
    f.write("{p}\n".format(p=os.environ["PYTHONPATH"].split(os.pathsep)))

#from eud import Eud
from device.simulated.eud import Eud
from philips_lights.light_driver import Light_Driver
from common.smap_tools.smap_tools import download_most_recent_point
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
import json

class Philips_Light(Eud):
    def __init__(self, config = None):
        self._device_type = "philips_light"
        # Call super constructor
        Eud.__init__(self, config)
        
        self._smap_info = config.get("smap", None)

        self._current_light_level = None
        self.light_server_info = config.get("light_server") 
        url = self.light_server_info.get("url")
        username = self.light_server_info.get("user") 
        pw = self.light_server_info.get("password")
        self.driver = Light_Driver(url, (username, pw))

        
    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        # just doing 1-price to get light level.  Light level should be between 0 and 1
        # and prices are currently between 0 and 1 so this works for the experiment
        # but will need to be changed if/when the range values price can take changes. 
        self.set_light_level(1.0 - new_price)
        
        # return flow to the rest of the LPDM stack
        super(Philips_Light, self).on_price_change(source_device_id, target_device_id, time, new_price)
        
    def lookup_power(self):
        if self._smap_info:
                stream_info = self._smap_info.get("power", None)
                if stream_info:
                    _, ts, value = download_most_recent_point(stream_info["smap_root"], stream_info["stream"])

        return value


    def on_time_change(self, new_time):
        power_use = self.lookup_power()
        self.broadcast_new_power(power_use)
        super(Philips_Light, self).on_time_change(new_time)
        
    def set_light_level(self, light_level):
        res = self.driver.set_light_level(light_level)        
        return res

