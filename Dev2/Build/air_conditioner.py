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
from Build.device import SECONDS_IN_DAY


class AirConditionerSimple(Eud):

    ##
    # @param compressor_temp_rate the cooling rate at the air conditioner (degrees C / hour).
    # @param heat_exchange_rate the rate of change in temperature as a result of the difference between internal and
    # external temperature
    def __init__(self, device_id, supervisor, msg_latency=0, schedule=None, time=0, connected_devices=None,
                 max_power_output=500.0, current_temp=25.0, temp_max_delta=0.5, base_set_point=23.0,
                 price_to_setpoint=None, precooling_enabled=False, precooling_price_threshold=None,
                 compressor_cooling_rate=2.0, heat_exchange_rate=0.1, setpoint_interval=600,
                 temperature_update_interval=300):

        super().__init__(device_id, "air_conditioner", supervisor, msg_latency=msg_latency, time=time,
                         schedule=schedule, connected_devices=connected_devices)

        self._max_power_output = max_power_output
        self._current_temperature = current_temp
        self._current_outdoor_temperature = None

        self._temperature_max_delta = temp_max_delta  # How much to let the temperature to vary around setpoint

        self._precooling_enabled = precooling_enabled
        self._precooling_price_threshold = precooling_price_threshold

        self._set_point = base_set_point  # The starting temperature set point
        self._setpoint_interval = setpoint_interval

        self._price_to_setpoint = price_to_setpoint  # A list of tuples of (price, setpoint).

        self._temperature_schedule = None

        self._compressor_cooling_rate = compressor_cooling_rate

        self._heat_exchange_rate = heat_exchange_rate
        self._compressor_is_on = False
        self._last_temperature_update_time = 0.0  # the time the last internal temperature update occurred
        self._temperature_update_interval = temperature_update_interval

    ##
    # @param temperature_schedule a list of tuples of (time, temperature) for outdoor temperatures.
    # TODO: Where is this? What do we do with it?
    def schedule_outdoor_temperature_events(self, temperature_schedule, total_runtime):
        curr_day = 0  # The current day in seconds
        while curr_day < total_runtime:
            for time, temp in temperature_schedule:
                temperature_event = Event(self.update_outdoor_temperature, temp)
                self.add_event(temperature_event, time + curr_day)
            curr_day += SECONDS_IN_DAY


    """ UNNECESSARY. Only need to do this when the price changes. 
        def schedule_setpoint_evaluation_events(self, total_runtime):
            curr_time = 0
            while curr_time < total_runtime:
                self.add_event(Event(self.reassess_setpoint), curr_time)
                curr_time += self._setpoint_interval
    """

    def schedule_temperature_change_events(self, total_runtime):
        curr_time = 0
        while curr_time < total_runtime:
            self.add_event(Event(self.reassess_setpoint), curr_time)
            curr_time += self._temperature_update_interval

    def reassess_setpoint(self):
        if self._price is None:
            return False
        new_set_point = self.get_setpoint_from_price(self._price)
        if new_set_point != self._set_point:
            self._set_point = new_set_point
            self._logger.debug(self.build_log_notation(
                message="setpoint changed to {}".format(new_set_point), tag="set_point", value=new_set_point))
            return True
        else:
            return False

    def get_setpoint_from_price(self, price):
        if self._price_to_setpoint is None:
            return self._set_point
        sorted_by_price = sorted(self._price_to_setpoint, key=lambda d: d[0])
        for price_val, setpoint in sorted_by_price:
            if price <= price_val:
                return setpoint
        return sorted_by_price[-1][1]

    def adjust_internal_temperature(self):
        """
        adjust the temperature of the device based on the indoor/outdoor temperature difference
        """
        if self._time > self._last_temperature_update_time:
            delta_t = ((self._time - self._last_temperature_update_time) / 3600.0)  # time difference in hours
            if self._compressor_is_on:
                # if the compressor is on adjust the internal temperature due to cooling
                delta_c = delta_t * self._compressor_cooling_rate
                self._current_temperature -= delta_c
                self._logger.debug(self.build_log_notation(
                    message="compressor adjustment", tag="comp_delta_c", value=delta_c))

            # calculate the indoor delta_t due to the outdoor temperature
            if self._current_outdoor_temperature is not None:
                # difference between indoor and outdoor temp
                delta_t = ((self._time - self._last_temperature_update_time) / 3600.0)
                delta_indoor_outdoor = self._current_outdoor_temperature - self._current_temperature
                delta_c = delta_t * delta_indoor_outdoor * self._heat_exchange_rate
                self._current_temperature += delta_c
                self._logger.info(self.build_log_notation(
                        message="Internal temperature", tag="internal_temperature", value=self._current_temperature))
                self._last_temperature_update_time = self._time

    # TODO: Understand this. Only missing component and we should be good.
    def precooling_update(self):
        if self._precooling_enabled and not self._in_operation:
            if self._precooling_price_threshold is None or self._price < self._precooling_price_threshold:
                self._logger.info(self.build_log_notation(
                    message="precooling device, price {}".format(self._price), tag="precool_on_off", value=1))
                self.turn_on()
        elif self._precooling_enabled and self._in_operation:
            # precooling is enabled and the device is on
            if not self.should_be_in_operation() and self._price >= self._precooling_price_threshold:
                self._logger.info(self.build_log_notation(
                    message="precooling device, price {}".format(self._price), tag="precool_on_off", value=0))
                self.turn_off()

    def control_compressor_operation(self):
        """turn the compressor on/off when needed"""
        # see if the current tempreature is outside of the allowable range
        # and check if the ac is able to turn its compressor on
        if self._set_point is None or not self._in_operation:
            return

        delta = self._current_temperature - self._set_point
        self._logger.debug(self.build_log_notation(
                           message="delta from setpoint: {}".format(delta), tag="delta_t", value=delta))
        if abs(delta) > self._temperature_max_delta:
            if delta > 0 and not self._compressor_is_on:
                # if the current temperature is above the set point and compressor is off, turn it on
                self.turn_on_compressor()
            elif delta < 0 and self._compressor_is_on:
                # if current temperature is below the set point and compressor is on, turn it off
                self.turn_off_compressor()

    def turn_on_compressor(self):
        """Turn on the compressor"""
        if self._in_operation:
            self._logger.debug(self.build_log_notation(message="compressor_on", tag="compressor_on_off", value=1))
            self._compressor_is_on = True
            # this should be 0

    def turn_off_compressor(self):
        if self._time - self._last_total_energy_update_time > 900: # TODO: Why this?
            self._compressor_is_on = False
            self._logger.debug(self.build_log_notation(message="turn off compressor", tag="compressor_on_off", value=0))

    def update_outdoor_temperature(self, new_temperature):
        self._current_outdoor_temperature = new_temperature

    def end_internal_operation(self):
        if self._compressor_is_on:
            self.turn_off_compressor()

    def begin_internal_operation(self):
        pass

    def calculate_desired_power_level(self):
        self.adjust_internal_temperature()
        self.reassess_setpoint()
        self.precooling_update()
        self.control_compressor_operation()


