"""
    Defines the base class for TuG system components.
"""
import os
import random
import logging
import coloredlogs
import pprint
import datetime
from notification import NotificationReceiver, NotificationSender

class Device(NotificationReceiver, NotificationSender):
    """
        Base class for TuG system components.

        Usage:
            To create a new device, define a new class that inherits from the Device class.

        Requirements:
            Must override the following methods:
                onPowerChange
                onPriceChange
                calculateNextTTIE

            Callbacks:
                If the device needs to broadcast changes in power, price, or time, the appropriate callback must be passed into the constructor in the configuration parameter:
                    broadcastNewPower,
                    broadcastNewPrice,
                    broadcastNewTTIE
    """
    def __init__(self, config):
        self._device_name = "device" if not self._device_name else self._device_name
        self._device_type = "device" if not "_device_type" in dir(self) or not self._device_type else self._device_type
        self._simulation_id = int(config["simulation_id"]) if type(config) is dict and "simulation_id" in config.keys() else None
        self._app_log_manager = config["app_log_manager"] if type(config) is dict and "app_log_manager" in config.keys() else None
        self._app_logger = config["logger"] if type(config) is dict and "logger" in config.keys() else None
        self._tug_logger = config["tug_logger"] if type(config) is dict and "tug_logger" in config.keys() else None
        self._config_time = config["config_time"] if type(config) is dict and "config_time" in config.keys() else 1
        self._uuid = config["uuid"] if type(config) is dict and "uuid" in config.keys() else None
        self._price = config["price"] if type(config) is dict and "price" in config.keys() else 0.0
        self._power_level = 0.0
        self._time = 0
        self._units = None
        self._in_operation = False
        self._ttie = None
        self._next_event = None
        # self._logger = None
        self._device_logger = None

        self._device_id = self._buildDeviceID()

        self._broadcastNewPriceCallback = config["broadcastNewPrice"] if type(config) is dict and  "broadcastNewPrice" in config.keys() and callable(config["broadcastNewPrice"]) else None
        self._broadcastNewPowerCallback = config["broadcastNewPower"] if type(config) is dict and "broadcastNewPower" in config.keys() and callable(config["broadcastNewPower"]) else None
        self._broadcastNewTTIECallback = config["broadcastNewTTIE"] if type(config) is dict and "broadcastNewTTIE" in config.keys() and callable(config["broadcastNewTTIE"]) else None

        self.setLogger()

        self.calculateNextTTIE()

        self.logMessage("initialized device #{} - {}".format(self._uuid, self._device_type))
        self.logMessage(pprint.pformat(config), app_log_level=None, device_log_level=logging.DEBUG)

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def uuid(self):
        return self._uuid;

    def deviceID(self):
        return self._device_id

    def _buildDeviceID(self):
        return "device_{0}".format(self._uuid if self._uuid else "not_specified")

    def deviceName(self):
        return self._device_name

    def tugSendMessage(self, action, is_initial_event, value, description=""):
        if self._tug_logger:
            self._tug_logger.logAction(self, self._time, action, is_initial_event, value, description)

    def status(self):
        return None

    def setLogger(self):
        self._device_logger = logging.getLogger("sim_{}_device_{}".format(self._simulation_id, self._uuid))
        self._device_logger.setLevel(logging.DEBUG)
        # coloredlogs.install(level='INFO', logger=logger)

        # create file handler which logs even debug messages
        self._app_logger.debug("app log manager")
        self._app_logger.debug(self)
        fh = logging.FileHandler(os.path.join(self._app_log_manager.simulationLogPath(), "device_{}_{}.log".format(self._uuid, self._device_type)), mode='w')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        colored_formatter = coloredlogs.ColoredFormatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # ch.setFormatter(formatter)
        ch.setFormatter(colored_formatter)
        fh.setFormatter(formatter)

        # add the handlers to logger
        self._device_logger.addHandler(ch)
        self._device_logger.addHandler(fh)
        return

    def logMessage(self, message='', app_log_level=logging.INFO, device_log_level=logging.DEBUG):
        "Logs a message using the loggin module, default debug level is set to INFO"
        time_string = "Day {0} {1} ({2})".format(1 + int(self._time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(self._time).strftime('%H:%M:%S'), self._time)
        message = "time: {}, device: {}, message: {}".format(time_string, self._device_name, message)
        if app_log_level is not None:
            self._app_logger.log(app_log_level, message)
        if device_log_level is not None:
            self._device_logger.log(device_log_level, message)

    def calculateNextTTIE(self):
        "Calculate the Time Till next Initial Event, this must be overriden for each derived class"
        raise Exception('Need to define method to calculate the next ttie (calculateNextTTIE)')

    def randomizeTiming(self):
        "Randomize timeing?"
        return random.randrange(-self._config_time, self._config_time, 1)

    def broadcastNewPrice(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewPriceCallback):
            self.logMessage("Broadcast new price {} from {}".format(new_price, self._device_name), app_log_level=None)
            self._broadcastNewPriceCallback(self._device_id, target_device_id, self._time, new_price)
        else:
            raise Exception("broadcastNewPrice has not been set for this device!")
        return

    def broadcastNewPower(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewPowerCallback):
            # self.logMessage("Broadcast new power (t = {0}, power = {1})".format(self._time, new_power), debug_level)
            self.logMessage("Broadcast new power {} from {}".format(new_power, self._device_name), app_log_level=None)
            self._broadcastNewPowerCallback(self._device_id, target_device_id, self._time, new_power)
        else:
            raise Exception("broadcastNewPower has not been set for this device!")
        return

    def broadcastNewTTIE(self, new_ttie, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewTTIECallback):
            # self.logMessage("Broadcast new ttie (t = {0}, ttie = {1})".format(self._time, new_ttie), debug_level)
            self.logMessage("Broadcast new TTIE {} from {}".format(new_ttie, self._device_name), app_log_level=None)
            self._broadcastNewTTIECallback(self._device_id, target_device_id, new_ttie - self._time)
        else:
            raise Exception("broadcastNewTTIE has not been set for this device!")
        return

    def timeOfDaySeconds(self):
        "Get the time of day in seconds"
        return self._time % (24 * 60 * 60)

    def getTTIE(self):
        return self._ttie

    def turnOn(self):
        "Turn on the device"
        self.logMessage("{} turned on".format(self._device_name))
        self._in_operation = True

    def turnOff(self):
        "Turn off the device"
        self.logMessage("{} turned off".format(self._device_name))
        self._in_operation = False

    def isOn(self):
        return self._in_operation

    def refresh(self):
        "Override to define operation for a device when a parameter has been reset and the device needs to be refreshed"

    def setScenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

