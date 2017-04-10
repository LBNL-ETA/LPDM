import os
import json

class OutdoorTemperature(object):
    def __init__(self):
        self._hourly_profile = None
        self._temperature_file_name = "weather_5_secs.json"

    def init(self):
        self.load_temperature_profile()

    def load_temperature_profile(self):
        "load the temperature profile from a json file"
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), self._temperature_file_name), 'r') as content_file:
            self._hourly_profile = json.loads(content_file.read())
