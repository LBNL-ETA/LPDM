"""
    Defines the base class for TuG system components.
"""
import random
import logging
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
        self._logger = None

        self._device_id = self._buildDeviceID()

        self._broadcastNewPriceCallback = config["broadcastNewPrice"] if type(config) is dict and  "broadcastNewPrice" in config.keys() and callable(config["broadcastNewPrice"]) else None
        self._broadcastNewPowerCallback = config["broadcastNewPower"] if type(config) is dict and "broadcastNewPower" in config.keys() and callable(config["broadcastNewPower"]) else None
        self._broadcastNewTTIECallback = config["broadcastNewTTIE"] if type(config) is dict and "broadcastNewTTIE" in config.keys() and callable(config["broadcastNewTTIE"]) else None

        self.setLogger()

        self.calculateNextTTIE()

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def deviceID(self):
        return self._device_id

    def _buildDeviceID(self):
        return "device_{0}".format(self._uuid if self._uuid else "not_specified")

    def deviceName(self):
        return self._device_name
        
    def tugLogAction(self, action, is_initial_event, value, description=""):
        if self._tug_logger:
            self._tug_logger.logAction(self, self._time, action, is_initial_event, value, description)

    def status(self):
        return None

    def setLogger(self):
        # logging.basicConfig(filename='myapp.log', level=logging.DEBUG)
        self._logger = logging.getLogger(self._device_name)
        self._logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self._logger.addHandler(ch)

        fh = logging.FileHandler(self.logFileName(), mode="w")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

        return

    def logMessage(self, message='', debug_level=logging.INFO):
        "Logs a message using the loggin module, default debug level is set to DEBUG"
        if debug_level == logging.DEBUG:
            self._logger.debug(message)
        elif debug_level == logging.INFO:
            self._logger.info(message)
        elif debug_level == logging.WARNING:
            self._logger.warning(message)
        elif debug_level == logging.ERROR:
            self._logger.error(message)
        elif debug_level == logging.CRITICAL:
            self._logger.critical(message)

    def logFileName(self):
        "Creates a log file name for the device"
        return 'log_' + '_'.join(self._device_name.split(" ")) + ".txt"

    def calculateNextTTIE(self):
        "Calculate the Time Till next Initial Event, this must be overriden for each derived class"
        raise Exception('Need to define method to calculate the next ttie (calculateNextTTIE)')

    def randomizeTiming(self):
        "Randomize timeing?"
        return random.randrange(-self._config_time, self._config_time, 1)

    def broadcastNewPrice(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewPriceCallback):
            # self.logMessage("Broadcast new price (t = {0}, price = {1})".format(self._time, new_price), debug_level)
            self._broadcastNewPriceCallback(self._device_id, target_device_id, self._time, new_price)
        else:
            raise Exception("broadcastNewPrice has not been set for this device!")
        return

    def broadcastNewPower(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewPowerCallback):
            # self.logMessage("Broadcast new power (t = {0}, power = {1})".format(self._time, new_power), debug_level)
            self._broadcastNewPowerCallback(self._device_id, target_device_id, self._time, new_power)
        else:
            raise Exception("broadcastNewPower has not been set for this device!")
        return
    
    def broadcastNewTTIE(self, new_ttie, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcastNewTTIECallback):
            # self.logMessage("Broadcast new ttie (t = {0}, ttie = {1})".format(self._time, new_ttie), debug_level)
            self._broadcastNewTTIECallback(self._device_id, target_device_id, new_ttie)
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
        self.logMessage("Device turned on")
        self._in_operation = True

    def turnOff(self):
        "Turn off the device"
        self.logMessage("Device turned off")
        self._in_operation = False

    def isOn(self):
        return self._in_operation

    def setScenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

