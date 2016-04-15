"""
    Implementation of an air conditioner
"""

from device import Device
import logging
import colors
import pprint

class AirConditioner(Device):
    """
        Device implementation of a grid controller.

        Use the battery to try and keep the diesel generator above 70% capacity
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the air conditioner

                keys:
                    "device_type" (string): Type of device
                    "device_name" (string): Name of the device
                    "max_power_use" (float): the maximum power output of the device
                    "current_temperature" (float): the current temperature inside the device
                    "current_set_point (float)": the initial set point
                    "temperature_max_delta" (float): the maximum amount that the temperature can increase by for every reassessment
                    "set_point_low" (float): the low value for the set point
                    "set_point_high" (float): the high value for the set point
                    "setpoint_reassesment_interval" (int): number of seconds between reassesing the set point
                    "price_range_low" (float): the low price reference for setpoint adjustment [$/kwh]
                    "price_range_high" (float): the high price reference for setpoint adjustment [$/kwh]
        """
        self._device_type = "air_conditioner"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "air_conditioner"

        # maximim power output, set to 4000 W if no value given
        self._max_power_use = float(config["max_power_use"]) if type(config) is dict and "max_power_use" in config.keys() else 4000.0

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
        self._set_point_low = float(config["set_point_low"]) if type(config) is dict and "set_point_low" in config.keys() else 0.5
        self._set_point_high = float(config["set_point_high"]) if type(config) is dict and "set_point_high" in config.keys() else 5.0
        self._setpoint_reassesment_interval = float(config["setpoint_reassesment_interval"]) if type(config) is dict and "setpoint_reassesment_interval" in config.keys() else 60.0 * 10.0
        self._price_range_low = float(config["price_range_low"]) if type(config) is dict and "price_range_low" in config.keys() else 0.2
        self._price_range_high = float(config["price_range_high"]) if type(config) is dict and "price_range_high" in config.keys() else 0.7
        self._cop = float(config["cop"]) if type(config) is dict and "cop" in config.keys() else 3.0
        self._number_of_people = None
        self._volume_m3 = float(config["volume_m3"]) if type(config) is dict and "volume_m3" in config.keys() else 3000 #volume of tent in m3
        self._heat_w_per_person = 120 # Heat (W) generated per person
        self._kwh_per_m3_1c = 1.0 / 3000.0 # 1 kwh to heat 3000 m3 by 1 C
        self._kj_per_m3_c = 1.2 # amount of energy (kj) it takees to heat 1 m3 by 1 C

        self._set_point_target = self._current_set_point
        self._temperature_hourly_profile = None
        self._current_outdoor_temperature = None
        self._temperature_update_interval = 60.0 * 10.0 # every 10 minutes?
        self._last_temperature_update_time = 0.0 # the time the last internal temperature update occured
        self._heat_gain_rate = None
        self._cop = 3.0
        self._max_c_delta = 10.0 #the maximum temeprature the ECU can handle in 1 hr
        self._compressor_max_c_per_kwh = self._max_c_delta / self._max_power_use

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

        self.computeHeatGainRate()
        self._temperature_hourly_profile = self.buildHourlyTemperatureProfile()
        self.logMessage("Hourly temperature profile: \n{}".format(pprint.pformat(self._temperature_hourly_profile, indent=4)))
        self.scheduleNextEvents()

    def getLogMessageString(self, message):
        return colors.colorize(Device.getLogMessageString(self, message), colors.Colors.BLUE)

    def buildHourlyTemperatureProfile(self):
        """
        these are average hourly tempeartures for edwards airforce base from august 2015
        """
        return [
            {"hour": 0, "hour_seconds": 3600.0 * 0, "value": 23.2},
            {"hour": 1, "hour_seconds": 3600.0 * 1, "value": 22.3},
            {"hour": 2, "hour_seconds": 3600.0 * 2, "value": 21.6},
            {"hour": 3, "hour_seconds": 3600.0 * 3, "value": 20.9},
            {"hour": 4, "hour_seconds": 3600.0 * 4, "value": 20.1},
            {"hour": 5, "hour_seconds": 3600.0 * 5, "value": 20.3},
            {"hour": 6, "hour_seconds": 3600.0 * 6, "value": 23.3},
            {"hour": 7, "hour_seconds": 3600.0 * 7, "value": 26.4},
            {"hour": 8, "hour_seconds": 3600.0 * 8, "value": 29.8},
            {"hour": 9, "hour_seconds": 3600.0 * 9, "value": 32.2},
            {"hour": 10, "hour_seconds": 3600.0 * 10, "value": 34.3},
            {"hour": 11, "hour_seconds": 3600.0 * 11, "value": 35.8},
            {"hour": 12, "hour_seconds": 3600.0 * 12, "value": 37.0},
            {"hour": 13, "hour_seconds": 3600.0 * 13, "value": 37.6},
            {"hour": 14, "hour_seconds": 3600.0 * 14, "value": 37.6},
            {"hour": 15, "hour_seconds": 3600.0 * 15, "value": 37.2},
            {"hour": 16, "hour_seconds": 3600.0 * 16, "value": 35.9},
            {"hour": 17, "hour_seconds": 3600.0 * 17, "value": 33.5},
            {"hour": 18, "hour_seconds": 3600.0 * 18, "value": 31.1},
            {"hour": 19, "hour_seconds": 3600.0 * 19, "value": 28.8},
            {"hour": 20, "hour_seconds": 3600.0 * 20, "value": 27.2},
            {"hour": 21, "hour_seconds": 3600.0 * 21, "value": 25.7},
            {"hour": 22, "hour_seconds": 3600.0 * 22, "value": 24.7},
            {"hour": 23, "hour_seconds": 3600.0 * 23, "value": 23.7}
        ]

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

        # reasses the setpoint for a price change event
        self.reassesSetpoint()
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
                    self.adjustInternalTemperature()
                    self.reassesSetpoint()
                    self.controlCompressorOperation()
                    remove_items.append(event)
                elif event["operation"] == "update_outdoor_temperature":
                    self.adjustInternalTemperature()
                    self.controlCompressorOperation()
                    self.processOutdoorTemperatureChange()
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
        self.scheduleNextOutdoorTemperatureChange()
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
        """
            determine the setpoint based on the current price and 24 hr. price history,
            and the current fuel price relative to price_range_low and price_range_high
        """

        # check to see if there's 24 hours worth of data, if there isn't exit
        if len(self._hourly_prices) < 24:
            return

        # adjust setpoint based on price
        if self._fuel_price > self._price_range_high:
            # price > price_range_high, then setpoint to max plus (price - price_range_high)/5
            new_setpoint = self._setpoint_high + (self._fuel_price - self._price_range_high) / 5.0
        elif self._fuel_price > self._price_range_low and self._fuel_price <= self._price_range_high:
            # fuel_price_low < fuel_price < fuel_price_high
            # determine the current price in relation to the past 24 hours of prices
            sorted_hourly_prices = sorted(self._hourly_prices)
            for i in xrange(24):
                if  self._fuel_price < sorted_hourly_prices[i]:
                    break
            price_percentile = float(i + 1) / 24.0
            new_setpoint = self._set_point_low + (self._set_point_high - self._set_point_low) * price_percentile
        else:
            # price < price_range_low
            new_setpoint = self._setpoint_low

        self.logMessage('reassesSetpoint: current setpoint = {}, new setpoint = {}'.format(self._current_set_point, new_setpoint));
        if new_setpoint != self._current_set_point:
            self._current_set_point = new_setpoint
            self.logMessage("calculated new setpoint as {}".format(new_setpoint))

    def adjustInternalTemperature(self):
        """
        adjust the temperature of the device based on the indoor/outdoor temperature difference
        """
        if self._time > self._last_temperature_update_time:
            if self.isOn():
                energy_used = self._max_power_use * (self._time - self._last_temperature_update_time) / 3600.0
                delta_c = self._compressor_max_c_per_kwh * energy_used
                self._current_temperature -= delta_c
                self.logMessage("calculated compressors decrease of C to {}".format(delta_c))


            if not self._current_outdoor_temperature is None:
                # difference between indoor and outdoor temp
                delta_indoor_outdoor = self._current_outdoor_temperature - self._current_temperature
                # calculate the fraction of the hour that has passed since the last update
                scale = (self._time - self._last_temperature_update_time) / 3600.0
                # calculate how much of that heat gets into the tent
                c_change = delta_indoor_outdoor * self._heat_gain_rate * scale

                self.logMessage("internal temperature changed from {} to {}".format(self._current_temperature, self._current_temperature + c_change))
                self._current_temperature += c_change
                self._last_temperature_update_time = self._time

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

    def scheduleNextOutdoorTemperatureChange(self):
        """schedule the next temperature update (in one hour)"""
        # first search for existing events
        search_events = [event for event in self._events if event["operation"] == "update_outdoor_temperature"]
        if not len(search_events):
            self._events.append({"time": self._time + self._temperature_update_interval, "operation": "update_outdoor_temperature"})

    def processOutdoorTemperatureChange(self):
        """Update the current outdoor temperature"""
        # get the time of day in seconds
        time_of_day = self.timeOfDaySeconds()
        found_temp = None
        for temp in self._temperature_hourly_profile:
            if temp["hour_seconds"] >= time_of_day:
                found_temp = temp
                break

        if found_temp:
            self.updateOutdoorTemperature(temp["value"])

    def updateOutdoorTemperature(self, new_temperature):
        "This method needs to be implemented by a device if it needs to act on a change in temperature"
        self._current_outdoor_temperature = new_temperature
        self.logMessage("Outdoor temperature changed to {}".format(new_temperature))
        return

    def computeHeatGainRate(self):
        """
        compute the heat gain
        want the ECU to be able to handle a 10C change in temperature
        """
        kwh_per_c = self._kj_per_m3_c * self._volume_m3 / 3600.0
        max_c_per_hr = self._max_power_use / 1000.0 / kwh_per_c * self._cop
        self._heat_gain_rate = self._max_c_delta / max_c_per_hr
        self.logMessage("set heat gain rate to {}".format(self._heat_gain_rate))

