from device.simulated.eud import Eud
import logging

from philips_lights.light_driver import Light_Driver
from common.smap_tools import smap_post

source_name= "Test Posting"

#timestamp = datetime.now()
#value = random.uniform(0, 1)
smap_api_key = "bIfgMJy0QPqDlp9lsfazwL70kyynrL9Guo5g" #chomp
#smap_api_key="MTTf1EZPRZELHr5hflJpsUus5ArBqS766NGi" #flexstorevh
smap_root = "http://chomp.lbl.gov/"
#smap_root="https://flexstorevh.lbl.gov"
timezone_string = "America/Los_Angeles"
als_unit=""
additional_metadata = {"location":"Flexlab"}

class Philips_Light(Eud):
    def __init__(self, config = None):
        Eud.__init__(self, config)
        self.driver = Light_Driver(self.on_light_reading)
        
    def on_light_reading(self, readings):
        for reading in readings:
            path_base="/Philips/" + reading.id
            als_path = path_base + "/ALS"
            led_power_path = path_base + "/LedPwr"
            battery_charge_power_path = path_base + "/BatChgPwr"
            
            smap_post(smap_root, smap_api_key, als_path, als_unit, "double", [[reading.timestamp, reading.als]], source_name, timezone_string, additional_metadata)
            smap_post(smap_root, smap_api_key, led_power_path, "W", "double", [[reading.timestamp, reading.led_power]], source_name, timezone_string, additional_metadata)
            smap_post(smap_root, smap_api_key, led_power_path, "W", "double", [[reading.timestamp, reading.battery_charge_power]], source_name, timezone_string, additional_metadata)
        
    def init(self):
        self.driver.init()