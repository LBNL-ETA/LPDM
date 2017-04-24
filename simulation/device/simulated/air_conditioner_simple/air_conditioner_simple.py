

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

import os
import json
import logging
from device.base.device import Device
from device.scheduler import LpdmEvent
from common.outdoor_temperature import OutdoorTemperature

class AirConditionerSimple(Device):
    def __init__(self, config):
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "air_conditioner_simple"
        self._device_name = config.get("device_name", "air_conditioner_simple")

        # maximim power output, default to 500 W if no value given
        self._max_power_output = config.get("max_power_output", 500.0)

        self._current_temperature = config.get("current_temperature", 25.0)
        self._temperature_max_delta = config.get("temperature_max_delta", 0.5)
        self._set_point = config.get("set_point", 23.0)
        self._setpoint_reassesment_interval = config.get("setpoint_reassesment_interval", 60.0 * 10.0) # 10 mins.
        # create the function that gives the set point from the current price of fuel
        # this will be changed on init() if there's a price schedule present
        self.get_set_point_from_price = lambda: self._set_point

        # precooling configuration
        precooling_config = config.get("precooling", {})
        self._precooling_enabled = precooling_config.get("enabled", False)
        # if set, any price below the threshold will start precooling
        # if set to None then precooling would always be enabled
        self._precooling_price_threshold = precooling_config.get("price_threshold", None)

        # sum the total energy used
        self._total_energy_use = 0.0
        self._last_total_energy_update_time = 0

        # holds the raw set point schedule
        self._set_point_schedule = None
        if type(config) is dict and config.has_key("set_point_schedule") and type(config["set_point_schedule"]) is list:
            self._set_point_schedule = config["set_point_schedule"]

        self._temperature_hourly_profile = None
        self._temperature_file_name = "weather_5_secs.json"
        self._current_outdoor_temperature = None

        self._temperature_update_interval = 60.0 * 5.0 # every 10 minutes?
        self._last_temperature_update_time = 0.0 # the time the last internal temperature update occured

        # rate at which the indoor temperature changes due to the compressor being on
        # units are C/hr
        self._temperature_change_rate_hr_comp = config.get("temperature_change_rate_hr_comp", 2.0)
        # rate at which the indoor temperature changes due to the outside air (oa)
        self._temperature_change_rate_hr_oa = config.get("temperature_change_rate_hr_oa", 0.1)


        # keep track of the compressor operation on/off
        self._compressor_is_on = False

    def init(self):
        """Setup the air conditioner prior to use"""
        self.setup_schedule()
        self.assign_set_point_generator()
        self.load_temperature_profile()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def assign_set_point_generator(self):
        """Assign the set point function"""
        self.get_set_point_from_price = self.build_set_point_function()

    def build_set_point_function(self):
        """Build a function that generates set points based on the price"""
        if self._set_point_schedule is None:
            # a price based schedule has not bee set, so use the default set point
            return lambda p: self._set_point
        else:
            # sort the schedule
            sorted_schedule = sorted(
                self._set_point_schedule,
                lambda a, b: cmp(a["price"], b["price"]) if type(a) is dict else cmp(a[0], b[0])
            )
            def gen(price):
                found = None
                for p in sorted_schedule:
                    if type(p) is dict:
                        if price <= p["price"]:
                            return p["set_point"]
                    elif type(p) is list:
                        if price <= p[0]:
                            return p[1]
                    else:
                        raise Exception("Invalid price schedule.")
                    found = p
                return found[1] if type(found) is list else found["set_point"]
            return gen

    def load_temperature_profile(self):
        "load the temperature profile from a json file"
        self._outdoor_temperature = OutdoorTemperature()
        self._outdoor_temperature.init()
        self._temperature_hourly_profile = self._outdoor_temperature._hourly_profile


    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turn_off()

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self._time = time
            if new_price != self._price:
                self._logger.debug(
                    self.build_message(
                        message="new price",
                        tag="receive_price",
                        value=new_price
                    )
                )
                self.set_price(new_price)
                self.adjust_internal_temperature()
                self.reasses_setpoint()
                self.precooling_update()
                self.control_compressor_operation()

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
                    message="ac should be on",
                    tag="capacity_change_on",
                    value=1
                )
            )
            self.turn_on()

    def process_events(self):
        "Process any events that need to be processed"
        Device.process_events(self)
        events_occurred = {
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

        if events_occurred["reasses_setpoint"] or events_occurred["update_outdoor_temperature"] or events_occurred["on"]:
            self.adjust_internal_temperature()
            if events_occurred["reasses_setpoint"]:
                self.reasses_setpoint()
            if events_occurred["update_outdoor_temperature"]:
                self.process_outdoor_temperature_change()
            self.precooling_update()
            self.control_compressor_operation()

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

    def schedule_next_events(self):
        "Schedule upcoming events if necessary"
        Device.schedule_next_events(self)
        # set the event for the hourly price calculation and setpoint reassesment
        self.set_reasses_setpoint_event()
        self.schedule_next_outdoor_temperature_change()

    def set_reasses_setpoint_event(self):
        "set the next event to calculate the set point"
        new_event = LpdmEvent(self._time + self._setpoint_reassesment_interval, "reasses_setpoint")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def set_new_fuel_price(self, new_price):
        """Set a new fuel price"""
        self._logger.debug(self.build_message(message="fuel_price", tag="fuel_price", value=new_price))
        self._price = new_price

    def reasses_setpoint(self):
        """
        Determine the set point based on the current price
        """
        if self._price is None:
            # can't do anything if price isn't set
            return False
        else:
            new_set_point = self.get_set_point_from_price(self._price)

        if new_set_point != self._set_point:
            self._set_point = new_set_point
            self._logger.debug(self.build_message(
                message="New setpoint {} -> {}".format(self._price, new_set_point),
                tag="set_point",
                value=new_set_point
            ))
            return True
        else:
            return False

    def adjust_internal_temperature(self):
        """
        adjust the temperature of the device based on the indoor/outdoor temperature difference
        """
        if self._time > self._last_temperature_update_time:
            if self._compressor_is_on:
                # if the compressor is on adjust the internal temperature due to cooling
                delta_t = ((self._time - self._last_temperature_update_time) / 3600.0)
                delta_c = delta_t * self._temperature_change_rate_hr_comp
                self._current_temperature -= delta_c
                self._logger.debug(self.build_message(
                    message="compressor adjustment",
                    tag="comp_delta_c",
                    value=delta_c
                ))

            # calculate the indoor delta_t due to the outdoor temperature
            if not self._current_outdoor_temperature is None:
                # difference between indoor and outdoor temp
                delta_t = ((self._time - self._last_temperature_update_time) / 3600.0)
                delta_indoor_outdoor = self._current_outdoor_temperature - self._current_temperature
                delta_c = delta_t * delta_indoor_outdoor * self._temperature_change_rate_hr_oa
                self._logger.debug(self.build_message(
                    message="oa adjustment",
                    tag="oa_delta_c",
                    value=delta_c
                ))
                self._current_temperature += delta_c
                self._logger.debug(
                    self.build_message(
                        message="Internal temperature",
                        tag="internal_temperature",
                        value=self._current_temperature
                    )
                )
                self._last_temperature_update_time = self._time

    def precooling_update(self):
        """Check if precooling is needed or not"""
        if self._precooling_enabled and not self._in_operation:
            if self._precooling_price_threshold is None or self._price < self._precooling_price_threshold:
                # only precool if precooling_enabled and
                # a) precooling_price_threshold is not set,
                # b) precoolling_price_threshold is set and the current price is below
                self._logger.info(self.build_message(
                    message="precooling turn on device, price at {}".format(self._price),
                    tag="precool_on_off",
                    value=1
                ))
                self.turn_on()
        elif self._precooling_enabled and self._in_operation:
            # precooling is enabled and the device is on
            if not self.should_be_in_operation() and self._price >= self._precooling_price_threshold:
                self._logger.info(self.build_message(
                    message="precooling turn on device, price at {}".format(self._price),
                    tag="precool_on_off",
                    value=0
                ))
                self.turn_off()

    def control_compressor_operation(self):
        """turn the compressor on/off when needed"""
        # see if the current tempreature is outside of the allowable range
        # and check if the ac is able to turn its compressor on
        if self._set_point is None or not self._in_operation:
            return

        delta = self._current_temperature - self._set_point
        self._logger.debug(self.build_message(
            message="calculate delta",
            tag="delta_t",
            value=delta
        ))
        if abs(delta) > self._temperature_max_delta:
            if delta > 0 and not self._compressor_is_on:
                # if the current temperature is above the set point and compressor is off, turn it on
                self.turn_on_compressor()
            elif delta < 0 and self._compressor_is_on:
                # if current temperature is below the set point and compressor is on, turn it off
                self.turn_off_compressor()

    def turn_on(self):
        """override the base class. if ac is on doesn't mean it's using power because compressor needs to be on"""
        if not self._in_operation:
            self._logger.info(self.build_message(message="turn on device", tag="on/off", value=1))
            self._in_operation = True

    def turn_off(self):
        "Turn off the device"
        if self._in_operation:
            if self._compressor_is_on:
                self.turn_off_compressor()
            self._in_operation = False
            self._logger.info(self.build_message(message="turn off device", tag="on/off", value=0))
            self._logger.info(self.build_message(
                message="Power level {}".format(self._power_level), tag="power", value=self._power_level
            ))

    def turn_on_compressor(self):
        """Turn on the compressor"""
        if self._in_operation:
            self._logger.debug(self.build_message(
                message="compressor_on", tag="compressor_on_off", value=1
            ))
            self._compressor_is_on = True
            # this should be 0
            self.sum_energy_used(self._power_level)
            previous_power_level = self._power_level
            self.set_power_level(self.calculate_power_level())
            if previous_power_level != self._power_level:
                self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)
        else:
            raise Exception("Trying to turn on compressor when not in operation")

    def turn_off_compressor(self):
        self._compressor_is_on = False
        self._logger.debug(self.build_message(
            message="compressor_on", tag="compressor_on_off", value=0
        ))
        if self._power_level != 0.0:
            self.sum_energy_used(self._power_level)
            self.set_power_level(0.0)
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

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
            self.update_outdoor_temperature(temp["value"])

    def update_outdoor_temperature(self, new_temperature):
        "This method needs to be implemented by a device if it needs to act on a change in temperature"
        self._current_outdoor_temperature = new_temperature

    def finish(self):
        "at the end of the simulation calculate the final total energy used"
        Device.finish(self)
        if self.is_on():
            self.sum_energy_used(self._max_power_output)

