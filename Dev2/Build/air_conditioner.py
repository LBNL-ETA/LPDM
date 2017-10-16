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
A simple model of a 'smart' air conditioner.
"""


from Build.eud import Eud
from Build.event import Event


class AirConditionerSimple(Eud):

    def __init__(self, device_id, supervisor, msg_latency=0, schedule=None, time=0, connected_devices=None,
                 max_power_output=500.0, current_temp=25.0, temp_max_delta=0.5, set_point=23.0,
                 precooling_enabled=False, precooling_price_threshold=None, compressor_temp_rate=2.0,
                 external_temp_rate=0.1, setpoint_interval=600, temperature_update_interval=300):

        super().__init__(device_id, "air_conditioner", supervisor, msg_latency=msg_latency, time=time,
                         schedule=schedule, connected_devices=connected_devices)

        self._max_power_output = max_power_output
        self._current_temperature = current_temp
        self._temperature_max_delta = temp_max_delta
        self._set_point = set_point
        self._setpoint_interval = setpoint_interval

        self._precooling_enabled = precooling_enabled
        self._precooling_price_threshold = precooling_price_threshold

        self._set_point_schedule = None  # TODO: CHANGE THIS. SETUP AC SCHEDULES.

        self._temperature_hourly_profile = None
        self._current_outdoor_temperature = None

        self._compressor_temp_rate = compressor_temp_rate

        self._external_temp_rate = external_temp_rate
        self._compressor_is_on = False
        self._last_temperature_update_time = 0.0  # the time the last internal temperature update occurred
        self._temperature_update_interval = temperature_update_interval

    ##
    # Loads a temperature schedule into the AC. Requires that
    # @param temp_schedule a list of tuples of (time, temperature) for outdoor temperatures.
    def load_temperature_profile(self, temperature_schedule):
        self.setup_schedule(temperature_schedule)

    def schedule_setpoint_evaluation_events(self, total_runtime):
        curr_time = 0
        while curr_time < total_runtime:
            self.add_event(Event(self.reassess_setpoint), curr_time)
            curr_time += self._setpoint_interval


    if self._time > self._last_temperature_update_time:
        self.adjust_internal_temperature()
        self.reasses_setpoint()
        self.precooling_update()
        self.control_compressor_operation()

    def reassess_setpoint(self):
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
        if ((self._time - self._last_total_energy_update_time)) > 900:

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
