

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
    Implementation of an air conditioner
"""

from device.base.device import Device
from device.scheduler import LpdmEvent
import os
import json
import logging
from set_point import SetPoint
from operation_status import OperationStatus
from common.outdoor_temperature import OutdoorTemperature

class Hvac(Device):
    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the air conditioner

                keys:
                    "device_name" (string): Name of the device
                    "max_power_output" (float): the maximum power output of the device
                    "current_temperature" (float): the current temperature inside the device
                    "current_set_point (float)": the initial set point
                    "temperature_max_delta" (float): the maximum amount that the temperature can increase by for every reassessment
                    "cop" (float) : coefficient of performance
                    "volume_m3" (int) [m3]: volume of space to condition
                    "setpoint_reassesment_interval" (int): number of seconds between reassesing the set point
                    "price_range_low" (float): the low price reference for setpoint adjustment [$/kwh]
                    "price_range_high" (float): the high price reference for setpoint adjustment [$/kwh]
                    "set_point_schedule" (list of int, float, float): hourly schedule of setpoints. e.g. [[0, 21.0, 25.0], [1, 21.0, 25.0], [2, 21.0, 25.0], ..., [23, 21.0, 25.0]]
                        schedule is an array with array elements for each hour of the day.
                        the array element for each hour has 3 items
                            1) hour
                            2) set_point_low
                            3) set_point_high
        """
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "hvac"
        self._device_name = config.get("device_name", "hvac")

        # maximim power output, default to 500 W if no value given
        self._cool_max_power_output = config.get("cool_max_power_output", 500.0)
        self._heat_max_power_output = config.get("heat_max_power_output", 500.0)

        # set the nominal price to be price of first hour of generation
        self._nominal_price = None
        self._nominal_price_calc_running = False
        self._nominal_price_list = []

        # hourly average price tracking
        self._hourly_prices = []
        self._hourly_price_list = []

        self._current_temperature = config.get("current_temperature", 1.0)
        self._temperature_max_delta = config.get("temperature_max_delta", 0.5)

        self._setpoint_reassesment_interval = config.get("setpoint_reassesment_interval", 60.0 * 10.0) # 10 mins.
        self._cop = config.get("cop", 3.0)
        self._set_point_factor = config.get("set_point_factor", 0.05)

        self._sp_cool = SetPoint()
        self._sp_cool.set_setpoint_factor(self._set_point_factor)
        self._sp_cool.set_point_low = config.get("cool_set_point_low", 21.0)
        self._sp_cool.set_point_high = config.get("cool_set_point_high", 25.0)
        self._sp_cool.price_range_low = config.get("cool_price_range_low", 0.2)
        self._sp_cool.price_range_high = config.get("cool_price_range_high", 0.7)

        self._sp_heat = SetPoint()
        self._sp_heat.set_setpoint_factor(self._set_point_factor)
        self._sp_heat.set_point_low = config.get("heat_set_point_low", 16.0)
        self._sp_heat.set_point_high = config.get("heat_set_point_high", 20.0)
        self._sp_heat.price_range_low = config.get("heat_price_range_low", 0.2)
        self._sp_heat.price_range_high = config.get("heat_price_range_high", 0.7)

        self._number_of_people = None
        self._volume_m3 = config.get("volume_m3", 3000)

        self._heat_w_per_person = 120 # Heat (W) generated per person
        self._kwh_per_m3_1c = 1.0 / 3000.0 # 1 kwh to heat 3000 m3 by 1 C
        self._kj_per_m3_c = 1.2 # amount of energy (kj) it takees to heat 1 m3 by 1 C

        # sum the total energy used
        self._total_energy_use = 0.0
        self._last_total_energy_update_time = 0

        if type(config) is dict and "cool_setpoint_schedule" in config.keys() and type(config["cool_setpoint_schedule"]) is list:
            self._sp_cool.set_schedule(config["cool_setpoint_schedule"])
        else:
            self._sp_cool.set_schedule(self.default_cool_setpoint_schedule())

        if type(config) is dict and "heat_setpoint_schedule" in config.keys() and type(config["heat_setpoint_schedule"]) is list:
            self._sp_heat.set_schedule(config["heat_setpoint_schedule"])
        else:
            self._sp_heat.set_schedule(self.default_heat_setpoint_schedule())

        self._outdoor_temperature = None
        self._temperature_hourly_profile = None
        self._temperature_file_name = "weather_5_secs.json"
        self._current_outdoor_temperature = None

        self._temperature_update_interval = 60.0 * 5.0 # every 5 minutes?
        self._last_temperature_update_time = 0.0 # the time the last internal temperature update occured
        self._heat_gain_rate = None
        self._max_c_delta = 10.0 #the maximum temeprature the ECU can handle in 1 hr
        self._compressor_max_c_per_kwh = 10.0 * (3000.0 / self._volume_m3) / 1000.0

        # keeps track of the hvac state
        self._operation_status = OperationStatus.OFF

        # keep track of the compressor operation on/off
        self._compressor_is_on = False

    def init(self):
        """Setup the air conditioner prior to use"""
        self.setup_schedule()
        self.set_initial_setpoints()
        self.compute_heat_gain_rate()
        self.load_temperature_profile()
        self.process_outdoor_temperature_change()
        self.reasses_setpoint()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def log_status(self):
        """Log the current status"""
        self._logger.debug(self.build_message(message="status: indoor_temp", tag="indoor_temp", value=self._current_temperature))
        self._logger.debug(self.build_message(message="status: outdoor_temp", tag="outdoor_temp", value=self._current_outdoor_temperature))
        self._logger.debug(self.build_message(message="status: is_cooling", tag="is_cooling", value=(1 if self.is_cooling() else 0)))
        self._logger.debug(self.build_message(message="status: is_heating", tag="is_heating", value=(1 if self.is_heating() else 0)))
        self._logger.debug(self.build_message(message="status: power_level", tag="power_level", value=self._power_level))
        self._logger.debug(self.build_message(message="status: status", tag="status", value=self._operation_status))
        self._logger.debug(self.build_message(message="status: sp_cool", tag="sp_cool", value=self._sp_cool.current_set_point))
        self._logger.debug(self.build_message(message="status: sp_heat", tag="sp_heat", value=self._sp_heat.current_set_point))

    def default_cool_setpoint_schedule(self):
        """generate a default setpoint schedule if none has been passed"""
        return [
            [0, 21.0, 25.0],
            [1, 21.0, 25.0],
            [2, 21.0, 25.0],
            [3, 21.0, 25.0],
            [4, 21.0, 25.0],
            [5, 21.0, 25.0],
            [6, 21.0, 25.0],
            [7, 21.0, 25.0],
            [8, 21.0, 25.0],
            [9, 21.0, 25.0],
            [10, 21.0, 25.0],
            [11, 21.0, 25.0],
            [12, 21.0, 25.0],
            [13, 21.0, 25.0],
            [14, 21.0, 25.0],
            [15, 21.0, 25.0],
            [16, 21.0, 25.0],
            [17, 21.0, 25.0],
            [18, 21.0, 25.0],
            [19, 21.0, 25.0],
            [20, 21.0, 25.0],
            [21, 21.0, 25.0],
            [22, 21.0, 25.0],
            [23, 21.0, 25.0],
        ]

    def default_heat_setpoint_schedule(self):
        """generate a default setpoint schedule if none has been passed"""
        return [
            [0, 16.0, 20.0],
            [1, 16.0, 20.0],
            [2, 16.0, 20.0],
            [3, 16.0, 20.0],
            [4, 16.0, 20.0],
            [5, 16.0, 20.0],
            [6, 16.0, 20.0],
            [7, 16.0, 20.0],
            [8, 16.0, 20.0],
            [9, 16.0, 20.0],
            [10, 16.0, 20.0],
            [11, 16.0, 20.0],
            [12, 16.0, 20.0],
            [13, 16.0, 20.0],
            [14, 16.0, 20.0],
            [15, 16.0, 20.0],
            [16, 16.0, 20.0],
            [17, 16.0, 20.0],
            [18, 16.0, 20.0],
            [19, 16.0, 20.0],
            [20, 16.0, 20.0],
            [21, 16.0, 20.0],
            [22, 16.0, 20.0],
            [23, 16.0, 20.0],
        ]

    def set_initial_setpoints(self):
        """set the initial set_point_low and set_point_high values"""
        self._sp_cool.set_initial_setpoints()
        self._sp_heat.set_initial_setpoints()

    def build_hourly_temperature_profile(self):
        """
        these are average hourly tempeartures for edwards airforce base from august 2015
        """
        return [
            {"hour": 0, "seconds": 3600.0 * 0, "value": 23.2},
            {"hour": 1, "seconds": 3600.0 * 1, "value": 22.3},
            {"hour": 2, "seconds": 3600.0 * 2, "value": 21.6},
            {"hour": 3, "seconds": 3600.0 * 3, "value": 20.9},
            {"hour": 4, "seconds": 3600.0 * 4, "value": 20.1},
            {"hour": 5, "seconds": 3600.0 * 5, "value": 20.3},
            {"hour": 6, "seconds": 3600.0 * 6, "value": 23.3},
            {"hour": 7, "seconds": 3600.0 * 7, "value": 26.4},
            {"hour": 8, "seconds": 3600.0 * 8, "value": 29.8},
            {"hour": 9, "seconds": 3600.0 * 9, "value": 32.2},
            {"hour": 10, "seconds": 3600.0 * 10, "value": 34.3},
            {"hour": 11, "seconds": 3600.0 * 11, "value": 35.8},
            {"hour": 12, "seconds": 3600.0 * 12, "value": 37.0},
            {"hour": 13, "seconds": 3600.0 * 13, "value": 37.6},
            {"hour": 14, "seconds": 3600.0 * 14, "value": 37.6},
            {"hour": 15, "seconds": 3600.0 * 15, "value": 37.2},
            {"hour": 16, "seconds": 3600.0 * 16, "value": 35.9},
            {"hour": 17, "seconds": 3600.0 * 17, "value": 33.5},
            {"hour": 18, "seconds": 3600.0 * 18, "value": 31.1},
            {"hour": 19, "seconds": 3600.0 * 19, "value": 28.8},
            {"hour": 20, "seconds": 3600.0 * 20, "value": 27.2},
            {"hour": 21, "seconds": 3600.0 * 21, "value": 25.7},
            {"hour": 22, "seconds": 3600.0 * 22, "value": 24.7},
            {"hour": 23, "seconds": 3600.0 * 23, "value": 23.7}
        ]

    def load_temperature_profile(self):
        "load the temperature profile from a json file"
        self._outdoor_temperature = OutdoorTemperature()
        self._outdoor_temperature.init()
        self._temperature_hourly_profile = self._outdoor_temperature._hourly_profile

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._operation_status != OperationStatus.OFF:
                self._time = time
                self.turn_off()

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        self.set_new_fuel_price(new_price)
        self.adjust_internal_temperature()
        self.reasses_setpoint()
        self.control_operation()

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self.process_events()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device has changed its capacity, check if the ac should be in operation"""
        self._time = time
        if not self._in_operation and self.should_be_in_operation():
            self._logger.debug(
                self.build_message(
                    message="should be on",
                    tag="capacity_change_on",
                    value=1
                )
            )
            self.turn_on()

    def process_events(self):
        "Process any events that need to be processed"

        events_occurred = {
            "set_nominal_price": False,
            "hourly_price_calculation": False,
            "set_point_range": False,
            "reasses_setpoint": False,
            "update_outdoor_temperature": False,
            "on": False,
            "off": False
        }

        # loop through the current events
        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                events_occurred[event.value] = True
                remove_items.append(event)

        # execute the found events in order
        if events_occurred["set_nominal_price"]:
            self.calculate_nominal_price()

        if events_occurred["hourly_price_calculation"]:
            self.calculate_hourly_price()

        if events_occurred["set_point_range"]:
            self.set_setpoint_range()

        if events_occurred["on"]:
            # self._logger.debug(self.build_message(message="on event found"))
            self.turn_on()
            found = filter(lambda d: d.value == "on", self._events)
            if len(found):
                self._current_event = found[0]
        elif events_occurred["off"]:
            # self._logger.debug(self.build_message(message="off event found"))
            self.turn_off()
            found = filter(lambda d: d.value == "off", self._events)
            if len(found):
                self._current_event = found[0]

        if events_occurred["reasses_setpoint"] \
        or events_occurred["update_outdoor_temperature"] \
        or events_occurred["set_point_range"] \
        or events_occurred["on"] \
        or events_occurred["off"]:
            self.adjust_internal_temperature()
            if events_occurred["reasses_setpoint"]:
                self.reasses_setpoint()
            if events_occurred["update_outdoor_temperature"]:
                self.process_outdoor_temperature_change()
            self.control_operation()

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

    def set_nominal_price_calculation_event(self):
        """
        calculate the nominal price using the avg of the first hour of operation
        so once the first price shows up start keeping track of the prices, then
        an hour later calculate the avg.
        """
        self._nominal_price_list = []
        self._nominal_price_calc_running = True
        new_event = LpdmEvent(self._time + 60.0 * 60.0, "set_nominal_price")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def calculate_nominal_price(self):
        if not self._nominal_price_calc_running:
            self._logger.info(self.build_message("Request to calculate nominal price but the event was never scheduled"))
            raise Exception("Nominal price calculation has not been started")

        self._nominal_price_calc_running = False
        self._nominal_price = sum(self._nominal_price_list) / float(len(self._nominal_price_list))

    def schedule_next_events(self):
        "Schedule upcoming events if necessary"
        Device.schedule_next_events(self)
        # set the event for the hourly price calculation and setpoint reassesment
        self.set_setpoint_range_event()
        self.set_reasses_setpoint_event()
        self.schedule_next_outdoor_temperature_change()

    def set_setpoint_range_event(self):
        """changes the set_point_low and set_point_high values based on the set_point_schedule (hour of day)"""
            # create a new event to execute in 60 minutes(?) if an event hasn't yet been scheduled
        new_event = LpdmEvent(self._time + 60 * 60.0, "set_point_range")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie <= new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def set_hourly_price_calculation_event(self):
        "set the next event to calculate the avg hourly prices"
        new_event = LpdmEvent(self._time + 60 * 60.0, "hourly_price_calculation")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie <= new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)
            self._hourly_price_list = []

    def set_reasses_setpoint_event(self):
        "set the next event to calculate the set point"
        new_event = LpdmEvent(self._time + self._setpoint_reassesment_interval, "reasses_setpoint")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie <= new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def calculate_hourly_price(self):
        """This should be called every hour to calculate the previous hour's average fuel price"""
        hour_avg = None
        if len(self._hourly_price_list):
            hour_avg = sum(self._hourly_price_list) / float(len(self._hourly_price_list))
        elif self._price is not None:
            hour_avg = self._price
        self._logger.debug(
            self.build_message(
                message="hourly price",
                tag="hourly_price",
                value=hour_avg
            )
        )

        self._hourly_prices.append(hour_avg)
        if len(self._hourly_prices) > 24:
            # remove the oldest item if more than 24 hours worth of data
            self._hourly_prices.pop(0)
        self._hourly_price_list = []

    def set_new_fuel_price(self, new_price):
        """Set a new fuel price"""
        self._logger.debug(
            self.build_message(
                message="fuel_price",
                tag="fuel_price",
                value=new_price
            )
        )
        self._price = new_price
        self._sp_heat.set_price(new_price)
        self._sp_cool.set_price(new_price)
        # if self._price < 1e5:
            # self.log_plot_value("fuel_price", self._price)

    def set_setpoint_range(self):
        """Change the setpoint range (low/high) for cooling and heating"""
        hour_of_day = int(self.time_of_day_seconds() / 3600)
        self._sp_cool.set_setpoint_range(hour_of_day)
        self._sp_heat.set_setpoint_range(hour_of_day)
        # log the new values
        # self._logger.debug(self.build_message(
            # message="set_setpoint_range", tag="setpoint_cool_low", value=self._sp_cool.set_point_low
        # ))
        # self._logger.debug(self.build_message(
            # message="set_setpoint_range", tag="setpoint_cool_high", value=self._sp_cool.set_point_high
        # ))
        # self._logger.debug(self.build_message(
            # message="set_setpoint_range", tag="setpoint_heat_low", value=self._sp_heat.set_point_low
        # ))
        # self._logger.debug(self.build_message(
            # message="set_setpoint_range", tag="setpoint_heat_high", value=self._sp_heat.set_point_high
        # ))


    def reasses_setpoint(self):
        """determine where the setpoint is between low/high for cooling and heating"""

        if self._sp_cool.reasses_setpoint():
            # cooling setpoint has changed
            self._logger.debug(self.build_message(
                message="cooling setpoint changed",
                tag="cool_setpoint",
                value=self._sp_cool.current_set_point
            ))
        if self._sp_heat.reasses_setpoint():
            # heating setpoint has changed
            self._logger.debug(self.build_message(
                message="heating setpoint changed",
                tag="heat_setpoint",
                value=self._sp_heat.current_set_point
            ))

    def adjust_internal_temperature(self):
        """
        adjust the temperature of the device based on the indoor/outdoor temperature difference
        """
        if self._time > self._last_temperature_update_time:
            if self.is_cooling():
                # if the compressor is on adjust the internal temperature
                energy_used = self._cool_max_power_output * (self._time - self._last_temperature_update_time) / 3600.0
                delta_c = self._compressor_max_c_per_kwh * energy_used
                orig = self._current_temperature
                self._current_temperature -= delta_c
            elif self.is_heating():
                # if the compressor is on adjust the internal temperature
                energy_used = self._heat_max_power_output * (self._time - self._last_temperature_update_time) / 3600.0
                delta_c = self._compressor_max_c_per_kwh * energy_used
                self._current_temperature += delta_c

            # difference between indoor and outdoor temp
            delta_indoor_outdoor = self._current_outdoor_temperature - self._current_temperature
            # calculate the fraction of the hour that has passed since the last update
            scale = (self._time - self._last_temperature_update_time) / 3600.0
            # calculate how much of that heat gets into the tent
            c_change = delta_indoor_outdoor * self._heat_gain_rate * scale

            orig = self._current_temperature
            self._current_temperature += c_change

            self._logger.debug(self.build_message(
                message="Internal temperature {} -> {}".format(orig, self._current_temperature),
                tag="internal_temperature",
                value=self._current_temperature
            ))
            self._last_temperature_update_time = self._time

    def turn_on(self):
        """override the base class. if device is on doesn't mean it's using power because compressor needs to be on"""
        if self._operation_status == OperationStatus.OFF:
            self._logger.info(self.build_message(message="turn on device", tag="on/off", value=1))
            self._operation_status = OperationStatus.STANDBY
            self._in_operation = True;

    def turn_off(self):
        "Turn off the device"
        if self._operation_status != OperationStatus.OFF:
            self.turn_off_cooling()
            self.turn_off_heating()
            self._operation_status = OperationStatus.OFF
            self._in_operation = False
            self._logger.info(self.build_message(message="turn off device", tag="on/off", value=0))

    def turn_on_cooling(self):
        """Turn on the compressor"""
        if self.is_off():
            raise Exception("Trying to turn on compressor when not in operation")
        elif self.is_heating():
            raise Exception("Trying to turn on cooling when currently heating")

        if self.is_stand_by():
            self._logger.debug(self.build_message(message="cooling on/off", tag="cooling_on_off", value=1))
            self._operation_status = OperationStatus.COOLING
            self.sum_energy_used(self._power_level)
            previous_power_level = self._power_level
            self.set_power_level(self._cool_max_power_output)
            if previous_power_level != self._power_level:
                self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def turn_on_heating(self):
        """Turn on heating"""
        if self.is_off():
            raise Exception("Trying to turn on compressor when not in operation")
        elif self.is_cooling():
            raise Exception("Trying to turn on heating when currently cooling")

        if self.is_stand_by():
            self._logger.debug(self.build_message(message="heating on/off", tag="heating_on_off", value=1))
            self._operation_status = OperationStatus.HEATING
            self.sum_energy_used(self._power_level)
            previous_power_level = self._power_level
            self.set_power_level(self._heat_max_power_output)
            if previous_power_level != self._power_level:
                self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def turn_off_cooling(self):
        """Stop cooling"""
        if self.is_cooling():
            self._logger.debug(self.build_message(message="cooling on/off", tag="cooling_on_off", value=0))
            self._operation_status = OperationStatus.STANDBY
            self.sum_energy_used(self._power_level)
            self.set_power_level(0.0)
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def turn_off_heating(self):
        """Stop cooling"""
        if self._operation_status == OperationStatus.HEATING:
            self._logger.debug(self.build_message(message="heating on/off", tag="heating_on_off", value=0))
            self._operation_status = OperationStatus.STANDBY
            self.sum_energy_used(self._power_level)
            self.set_power_level(0.0)
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def should_heat(self):
        """Should be heating?"""
        delta =  self._sp_heat.current_set_point - self._current_temperature
        return delta > self._temperature_max_delta and self._current_temperature < self._sp_heat.current_set_point

    def should_cool(self):
        """Should be cooling?"""
        delta = self._current_temperature - self._sp_cool.current_set_point
        return delta > self._temperature_max_delta and self._current_temperature > self._sp_cool.current_set_point

    def is_cooling(self):
        return self._operation_status == OperationStatus.COOLING

    def is_heating(self):
        return self._operation_status == OperationStatus.HEATING

    def is_off(self):
        return self._operation_status == OperationStatus.OFF

    def is_stand_by(self):
        return self._operation_status == OperationStatus.STANDBY

    def control_operation(self):
        """control the hvac: turn on/off heating/cooling"""
        # see if the current tempreature is outside of the allowable range
        # and check if the ac is able to turn its compressor on
        if self._operation_status == OperationStatus.OFF:
            return

        if self.should_heat():
            # temperature is below the heating setpoint
            if self.is_cooling():
                # if currently cooling then something is wrong
                raise Exception("trying to heat, but currently cooling")
            if self.is_off():
                self.turn_on()
            self.turn_on_heating()
        elif not self.should_heat() and self.is_heating():
            self.turn_off_heating()
        elif self.should_cool():
            # temperature is above the cooling set point
            if self.is_heating():
                # if currently heating then something is wrong
                raise Exception("trying to cool, but currently heating")
            if self.is_off():
                self.turn_on()
            self.turn_on_cooling()
        elif not self.should_cool() and self.is_cooling():
            self.turn_off_cooling()

    def sum_energy_used(self, power_level):
        self._total_energy_use += power_level * (self._time - self._last_total_energy_update_time) / (1000 * 3600)
        self._last_total_energy_update_time = self._time

    def schedule_next_outdoor_temperature_change(self):
        """schedule the next temperature update (in one hour)"""
        new_event = LpdmEvent(self._time + self._temperature_update_interval, "update_outdoor_temperature")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def process_outdoor_temperature_change(self):
        """Update the current outdoor temperature"""
        # get the time of day in seconds
        time_of_day = self.time_of_day_seconds()
        found_temp = None
        for temp in self._temperature_hourly_profile:
            if temp["seconds"] >= time_of_day:
                found_temp = temp
                break

        if found_temp:
            self._logger.debug(self.build_message(
                message="new outdoor temperature", tag="outdoor_temp", value=temp["value"]
            ))
            self.update_outdoor_temperature(temp["value"])

    def update_outdoor_temperature(self, new_temperature):
        "This method needs to be implemented by a device if it needs to act on a change in temperature"
        self._current_outdoor_temperature = new_temperature

    def compute_heat_gain_rate(self):
        """
        compute the heat gain
        want the ECU to be able to handle a 10C change in temperature
        """
        kwh_per_c = self._kj_per_m3_c * self._volume_m3 / 3600.0
        # TODO: Check the equation below because it depends on the power output of the device, but there are currently 2 (1 for heating and 1 for cooling)
        max_c_per_hr = self._cool_max_power_output / 1000.0 / kwh_per_c * self._cop
        self._heat_gain_rate = self._max_c_delta / max_c_per_hr

    def finish(self):
        "at the end of the simulation calculate the final total energy used"
        Device.finish(self)
        if self.is_on():
            self.sum_energy_used(self._max_power_output)

