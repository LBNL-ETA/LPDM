"""
    Implementation of an refrigerator
"""

from device import Device
import logging
import colors
import pprint

class Refrigerator(Device):
    """
        Device implementation of a Refrigerator
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the refrigerator

                keys:
                    "device_type" (string): Type of device
                    "device_name" (string): Name of the device
                    "max_power_use" (float): the maximum power output of the device
                    "current_temperature" (float): the current temperature inside the device
                    "current_set_point (float)": the initial set point
                    "temperature_max_delta" (float): the maximum variation between the setpoint and actual temperature for every reassesment
                    "temperature_increment" (float): the maximum amount that the temperature can increase by for every reassessment
                    "set_point_low" (float): the low value for the set point
                    "set_point_high" (float): the high value for the set point
                    "setpoint_reassesment_interval" (int): number of seconds between reassesing the set point
        """
        self._device_type = "refrigerator"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "refrigerator"

        # maximim power output, set to 3500 W if no value given
        self._max_power_use = float(config["max_power_use"]) if type(config) is dict and "max_power_use" in config.keys() else 3500.0

        self._fuel_price = None

        # set the nominal price to be price of first hour of generation
        self._nominal_price = None
        self._nominal_price_calc_running = False
        self._nominal_price_list = []

        # hourly average price tracking
        self._hourly_prices = []
        self._hourly_price_list = []

        self._current_temperature = float(config["current_temperature"]) if type(config) is dict and "current_temperature" in config.keys() else 2.5
        self._current_set_point = float(config["current_set_point"]) if type(config) is dict and "current_set_point" in config.keys() else 2.5
        self._temperature_max_delta = float(config["temperature_max_delta"]) if type(config) is dict and "temperature_max_delta" in config.keys() else 0.5
        self._temperature_increment = float(config["temperature_increment"]) if type(config) is dict and "temperature_increment" in config.keys() else 0.5
        self._set_point_low = float(config["set_point_low"]) if type(config) is dict and "set_point_low" in config.keys() else 0.5
        self._set_point_high = float(config["set_point_high"]) if type(config) is dict and "set_point_high" in config.keys() else 5.0
        self._setpoint_reassesment_interval = float(config["setpoint_reassesment_interval"]) if type(config) is dict and "setpoint_reassesment_interval" in config.keys() else 60.0 * 10.0

        self._set_point_target = self._current_set_point

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

    def getLogMessageString(self, message):
        return colors.colorize(Device.getLogMessageString(self, message), colors.Colors.BLUE)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        self.logMessage("Price change received (new_price = {}, source_device_id = {}, target_device_id = {})".format(new_price, source_device_id, target_device_id))

        if self._nominal_price is None:
            if not self._nominal_price_calc_running:
                # if the nominal price has not be calculated or is not running
                # then schedule the event and log the prices
                self.setNominalPriceCalculationEvent()
            self._nominal_price_list.append(new_price)

        # add the price to the list of prices for the hourly avg calculation
        self._hourly_price_list.append(new_price)
        self.setNewFuelPrice(new_price)
        return

    def onTimeChange(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time

        self.processEvents()
        self.scheduleNextEvents()
        self.calculateNextTTIE()
        return

    def processEvents(self):
        "Process any events that need to be processed"
        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "set_nominal_price":
                    self.calculateNominalPrice()
                    remove_items.append(event)
                elif event["operation"] == "hourly_price_calculation":
                    self.calculateHourlyPrice()
                    remove_items.append(event)
                elif event["operation"] == "reasses_setpoint":
                    self.adjustTemperature()
                    self.reassesSetpoint()
                    self.controlCompressorOperation()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return

    def setNominalPriceCalculationEvent(self):
        """
        calculate the nominal price using the avg of the first hour of operation
        so once the first price shows up start keeping track of the prices, then
        an hour later calculate the avg.
        """
        self._events.append({"time": self._time + 60.0 * 60.0, "operation": "set_nominal_price"})
        self._nominal_price_list = []
        self._nominal_price_calc_running = True

    def calculateNominalPrice(self):
        if not self._nominal_price_calc_running:
            self.logMessage("Request to calculate nominal price but the event was never scheduled", device_log_level=logging.CRITICAL, app_log_level=logging.CRITICAL)
            raise Exception("Nominal price calculation has not been started")

        self._nominal_price_calc_running = False
        self._nominal_price = sum(self._nominal_price_list) / float(len(self._nominal_price_list))
        self.logMessage("set nominal price: {}".format(self._nominal_price))

    def scheduleNextEvents(self):
        "Schedule upcoming events if necessary"
        # set the event for the hourly price calculation and setpoint reassesment
        self.setHourlyPriceCalculationEvent()
        self.setReassesSetpointEvent()
        return

    def setHourlyPriceCalculationEvent(self):
        "set the next event to calculate the avg hourly prices"
        found_events = filter(lambda x: x["operation"] == "hourly_price_calculation", self._events)
        if not len(found_events):
            # create a new event to execute in 1 hour if an event hasn't yet been scheduled
            self._events.append({"time": self._time + 60.0 * 60.0, "operation": "hourly_price_calculation"})
            self._hourly_price_list = []

    def setReassesSetpointEvent(self):
        "set the next event to calculate the set point"
        found_events = filter(lambda x: x["operation"] == "reasses_setpoint", self._events)
        if not len(found_events):
            # create a new event to execute in 10 minutes(?) if an event hasn't yet been scheduled
            self._events.append({"time": self._time + self._setpoint_reassesment_interval, "operation": "reasses_setpoint"})

    def calculateHourlyPrice(self):
        """This should be called every hour to calculate the previous hour's average fuel price"""
        hour_avg = None
        if len(self._hourly_price_list):
            hour_avg = sum(self._hourly_price_list) / float(len(self._hourly_price_list))
        elif self._fuel_price is not None:
            hour_avg = self._fuel_price

        self._hourly_prices.append(hour_avg)
        if len(self._hourly_prices) > 24:
            # remove the oldest item if more than 24 hours worth of data
            self._hourly_prices.pop(0)

        self._hourly_price_list = []

    def setNewFuelPrice(self, new_price):
        """Set a new fuel price"""
        self.logMessage("New fuel price = {}".format(new_price), app_log_level=None)
        self._fuel_price = new_price

    def reassesSetpoint(self):
        """determine the setpoint based on the current price and 24 hr. price history"""

        # check to see if there's 24 hours worth of data, if there isn't exit
        if len(self._hourly_prices) < 24:
            return

        # determine the current price in relation to the past 24 hours of prices
        sorted_hourly_prices = sorted(self._hourly_prices)
        for i in xrange(24):
            if  self._fuel_price < sorted_hourly_prices[i]:
                break

        price_percentile = float(i + 1) / 24.0
        new_setpoint = self._set_point_low + (self._set_point_high - self._set_point_low) * price_percentile
        if new_setpoint != self._current_set_point:
            self._current_set_point = new_setpoint
            self.logMessage("calculated new setpoint as {}".format(new_setpoint))

    def adjustTemperature(self):
        """
        adjust the temperature of the device
        temperature increases by 'temperature_increment' if generator is on
        and decreases by 'temperature_increment' if generator is off
        """

        if self.isOn():
            self._current_temperature -= self._temperature_increment
            self.logMessage("Decrease temperature to {}".format(self._current_temperature))
        else:
            self._current_temperature += self._temperature_increment
            self.logMessage("Increase temperature to {}".format(self._current_temperature))


    def controlCompressorOperation(self):
        """turn the compressor on/off when needed"""
        # see if the current tempreature is outside of the allowable range
        delta = self._current_temperature - self._current_set_point
        if abs(delta) > self._temperature_max_delta:
            if delta > 0 and not self.isOn():
                # if the current temperature is above the set point and compressor is off, turn it on
                self.turnOn()
                self.broadcastNewPower(self._max_power_use)
            elif delta < 0 and self.isOn():
                # if current temperature is below the set point and compressor is on, turn it off
                self.turnOff()
                self.broadcastNewPower(0.0)

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcastNewTTIE(ttie)



