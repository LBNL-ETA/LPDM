

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
    Defines the base class for TuG system components.
"""
import os
import random
import logging
import pprint
import datetime
import requests
import json
from notification import NotificationReceiver, NotificationSender
from plot import Plot

class Device(NotificationReceiver, NotificationSender):
    """
        Base class for TuG system components.

        Usage:
            To create a new device, define a new class that inherits from the Device class.

        Requirements:
            Must override the following methods:
                on_power_change
                on_price_change
                calculate_next_ttie

            Callbacks:
                If the device needs to broadcast changes in power, price, or time, the appropriate callback must be passed into the constructor in the configuration parameter:
                    broadcast_new_power,
                    broadcast_new_price,
                    broadcast_new_ttie
    """
    def __init__(self, config):
        self._device_name = "device" if not self._device_name else self._device_name
        self._device_type = "device" if not "_device_type" in dir(self) or not self._device_type else self._device_type
        self._simulation_id = int(config["simulation_id"]) if type(config) is dict and "simulation_id" in config.keys() else None
        self._app_log_manager = config["app_log_manager"] if type(config) is dict and "app_log_manager" in config.keys() else None
        self._app_logger = config["logger"] if type(config) is dict and "logger" in config.keys() else None
        self._config_time = config["config_time"] if type(config) is dict and "config_time" in config.keys() else 1
        self._uuid = config["uuid"] if type(config) is dict and "uuid" in config.keys() else None
        self._price = config["price"] if type(config) is dict and "price" in config.keys() else 0.0
        self._static_price = True if type(config) is dict and "static_price" in config.keys() and config["static_price"] else False
        self._dashboard = config["dashboard"] if type(config) is dict and "dashboard" in config.keys() else None
        self._headless = config["headless"] if type(config) is dict and config.has_key("headless") else False
        self._plot = None
        if type(config) is dict and config.has_key("plot_config"):
            self._plot = Plot(config["plot_config"])

        self._dashboard_url = None
        self._power_level = 0.0
        self._time = 0
        self._units = None
        self._in_operation = False
        self._ttie = None
        self._next_event = None
        # self._logger = None
        self._device_logger = None

        self._device_id = self._build_device_id()

        self._broadcast_new_price_callback = config["broadcast_new_price"] if type(config) is dict and  "broadcast_new_price" in config.keys() and callable(config["broadcast_new_price"]) else None
        self._broadcast_new_power_callback = config["broadcast_new_power"] if type(config) is dict and "broadcast_new_power" in config.keys() and callable(config["broadcast_new_power"]) else None
        self._broadcast_new_ttie_callback = config["broadcast_new_ttie"] if type(config) is dict and "broadcast_new_ttie" in config.keys() and callable(config["broadcast_new_ttie"]) else None

        # Setup logging
        self.set_logger()
        self.set_tug_logger()

        if self._plot:
            self._plot.set_file_paths(self._app_log_manager.simulation_log_path())

        self.calculate_next_ttie()

        self.log_message("initialized device #{} - {}".format(self._uuid, self._device_type))

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def finish(self):
        "Gets called at the end of the simulation"
        pass

    def uuid(self):
        return self._uuid;

    def device_id(self):
        return self._device_id

    def _build_device_id(self):
        return "device_{0}".format(self._uuid if self._uuid else "not_specified")

    def device_name(self):
        return self._device_name

    def out_of_fuel(self):
        return self._price > 1e5

    def set_tug_logger(self):
        """ Setup the logging for the TuG dashboard, send info directly to dashboard server via http post """
        if self._dashboard:
            self._dashboard_url = 'http://{0}:{1}/api/simulation_event'.format(self._dashboard["host"], self._dashboard["port"])
            # r = requests.post(url, data=data, allow_redirects=True)
            # print r.content
            # self._logging_http_request = urllib2.Request(url)
            # self._logging_http_request.add_header('Content-Type', 'application/json')

    def tug_send_message(self, action, is_initial_event, value, description=""):
        if self._dashboard_url:
            try:
                payload = {
                    "time": self._time,
                    "time_string": "Day {0} {1}".format(1 + int(self._time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(self._time).strftime('%H:%M:%S')),
                    "socket_id": self._dashboard["socket_id"],
                    "client_id": self._dashboard["client_id"],
                    "device_name": self.device_name(),
                    "is_initial_event": is_initial_event,
                    "uuid": self.uuid(),
                    "action": action,
                    "values": value,
                    "description": description
                }
                # payload = {"test": 1}
                self._dashboard_url
                r = requests.post(self._dashboard_url, data=payload)
                # response = urllib2.urlopen(self._logging_http_request, json.dumps(payload))
                # print response
            except Exception as inst:
                print 'http post error'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to be printed directly
                # x, y = inst.args
                # print 'x =', x
                # print 'y =', y
                raise

    def generate_plots(self):
        if self._plot:
            self._plot.generate_plots()
        if hasattr(self, '_battery') and self._battery:
            self._battery.generate_plots()
        if hasattr(self, '_pv') and self._pv:
            self._pv.generate_plots()

    def log_plot_value(self, parameter, value):
        """log values used for plots"""
        if self._plot:
            self._plot.log_value(parameter, self._time, value)

    def status(self):
        return None

    def set_logger(self):
        self._device_logger = logging.getLogger("sim_{}_device_{}".format(self._simulation_id, self._uuid))
        self._device_logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        self._app_logger.debug("app log manager")
        self._app_logger.debug(self)
        fh = logging.FileHandler(os.path.join(self._app_log_manager.simulation_log_path(), "device_{}_{}.log".format(self._uuid, self._device_type)), mode='w')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # ch.setFormatter(formatter)
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # add the handlers to logger
        self._device_logger.addHandler(ch)
        self._device_logger.addHandler(fh)
        return

    def log_message(self, message='', app_log_level=logging.INFO, device_log_level=logging.DEBUG, tag=None, value=None):
        "Logs a message using the loggin module, default debug level is set to INFO"
        message = self.get_log_message_string(message, tag, value)
        if app_log_level is not None:
            self._app_logger.log(app_log_level, message)
        if device_log_level is not None:
            self._device_logger.log(device_log_level, message)

    def get_log_message_string(self, message, tag=None, value=None):
        time_string = "Day {0} {1} ({2})".format(
                1 + int(self._time / (60 * 60 * 24)),
                datetime.datetime.utcfromtimestamp(self._time).strftime('%H:%M:%S'), self._time
        )
        return "time_string: {}, time_value: {}, device: {}, message: {}, tag: {}, value: {}".format(
                time_string, self._time, self._device_name, message, tag, value)


    def calculate_next_ttie(self):
        "Calculate the Time Till next Initial Event, this must be overriden for each derived class"
        raise Exception('Need to define method to calculate the next ttie (calculate_next_ttie)')

    def randomize_timing(self):
        "Randomize timeing?"
        return random.randrange(-self._config_time, self._config_time, 1)

    def broadcast_new_price(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_price_callback):
            self.log_message(
                message="Broadcast new price {} from {}".format(new_price, self._device_name),
                tag="broadcast_price",
                value=new_price
            )
            self._broadcast_new_price_callback(self._device_id, target_device_id, self._time, new_price)
        else:
            raise Exception("broadcast_new_price has not been set for this device!")
        return

    def broadcast_new_power(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_power_callback):
            self.log_message("Broadcast new power {} from {}".format(new_power, self._device_name), app_log_level=None)
            self.log_message(
                message="Broadcast new power {} from {}".format(new_power, self._device_name),
                tag="broadcast_power",
                value=new_power
            )
            self._broadcast_new_power_callback(self._device_id, target_device_id, self._time, new_power)
        else:
            raise Exception("broadcast_new_power has not been set for this device!")
        return

    def broadcast_new_ttie(self, new_ttie, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_ttie_callback):
            # self.log_message(
                # message="Broadcast new TTIE {} from {}".format(new_ttie, self._device_name),
                # tag="ttie",
                # value=new_ttie
            # )
            self._broadcast_new_ttie_callback(self._device_id, target_device_id, new_ttie - self._time)
        else:
            raise Exception("broadcast_new_ttie has not been set for this device!")
        return

    def time_of_day_seconds(self):
        "Get the time of day in seconds"
        return self._time % (24 * 60 * 60)

    def get_ttie(self):
        return self._ttie

    def turn_on(self):
        "Turn on the device"
        self.log_message("{} turned on".format(self._device_name), tag="on/off", value=1)
        self._in_operation = True

    def turn_off(self):
        "Turn off the device"
        self.log_message("{} turned off".format(self._device_name), tag="on/off", value=0)
        self._in_operation = False

    def is_on(self):
        return self._in_operation

    def refresh(self):
        "Override to define operation for a device when a parameter has been reset and the device needs to be refreshed"
        return None

    def set_scenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

