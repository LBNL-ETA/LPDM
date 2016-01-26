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
                    "device_name" (string): Name of the device
        """
        self._device_type = "air_conditioner"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "air_conditioner"

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
        self._set_point_low = float(config["set_point_low"]) if type(config) is dict and "set_point_low" in config.keys() else 0.5
        self._set_point_high = float(config["set_point_high"]) if type(config) is dict and "set_point_high" in config.keys() else 5.0
        self._temperature_reassesment_time = float(config["temperature_reassesment_time"]) if type(config) is dict and "temperature_reassesment_time" in config.keys() else 60.0 * 10.0

        self._events = []

        # call the super constructor
        Device.__init__(self, config)

    def getLogMessageString(self, message):
        return colors.colorize(Device.getLogMessageString(self, message), colors.Colors.BLUE)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        # self.logMessage("received power change, new power = {}, source_device_id = {}, target_device_id = {}".format(new_power, source_device_id, target_device_id))

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
        # self.scheduleNextEvents()
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

    def setHourlyPriceCalculationEvent(self):
        "set the next event to calculate the avg hourly prices"
        self._events.append({"time": self._time + 60.0 * 60.0, "operation": "hourly_price_calculation"})
        self._hourly_price_list = []

    def calculateHourlyPrice(self):
        """This should be called every hour to calculate the previous hour's average fuel price"""
        hour_avg = None
        if len(self._hourly_price_list):
            hour_avg = sum(self._hourly_price) / float(len(self._hourly_price))
        elif self._fuel_price is not None:
            hour_avg = self._fuel_price

        self._hourly_prices.append(hour_avg)
        if len(self._hourly_prices) > 24:
            # remove the oldest item if more than 24 hours worth of data
            x.pop(0)

        self._hourly_price_list = []

    # def setNextBatteryUpdateEvent(self):
        # "If the battery is on update its state of charge every X number of seconds"
        # self._events.append({"time": self._time + self._check_battery_soc_rate, "operation": "battery_status"})

    # def scheduleNextEvents(self):
        # "Schedule upcoming events if necessary"
        # if self._battery:
            # # if the battery is charging/discharging then check out the state_of_charge in self._check_battery_soc_rate seconds
            # search_events = [event for event in self._events if event["operation"] == "battery_status"]
            # if not len(search_events):
                # self.setNextBatteryUpdateEvent()
        # return

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self._ttie = ttie
            self.broadcastNewTTIE(ttie)

    def setNewFuelPrice(self, new_price):
        """Set a new fuel price"""
        self.logMessage("New fuel price = {}".format(new_price), app_log_level=None)
        self._fuel_price = new_price

