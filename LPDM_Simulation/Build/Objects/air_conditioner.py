########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""
A simple model of a 'smart' air conditioner.
"""


from Build.Simulation_Operation.support import SECONDS_IN_DAY
from Build.Simulation_Operation.event import Event
from Build.Objects.eud import Eud


class AirConditionerSimple(Eud):

    ##
    # @param compressor_operating_power how much energy the device requires to keep the compressor in operation
    # @param compressor_temp_rate the cooling rate at the air conditioner (degrees C / hour).
    # @param initial_temp: The initial internal temperature of the air conditioner
    # @param initial_setpoint: initial setpoint of this device
    # @param heat_exchange_rate the rate of change in temperature as a result of the difference between internal and
    # external temperature
    # @param price_to_setpoint a list of lists of price, setpoint for this device to modify setpoint based on price
    def __init__(self, device_id, supervisor, msg_latency=0, schedule=None, multiday=0, total_runtime=SECONDS_IN_DAY,
                 time=0,
                 connected_devices=None, compressor_operating_power=500.0, initial_temp=25.0, temp_max_delta=0.5,
                 initial_set_point=23.0, price_to_setpoint=None, temperature_schedule=None,
                 compressor_cooling_rate=2.0, heat_exchange_rate=0.1,
                 modulation_interval=300):

        super().__init__(device_id, "air_conditioner", supervisor, msg_latency=msg_latency, time=time,
                         modulation_interval=modulation_interval, total_runtime=total_runtime, multiday=multiday,
                         schedule=schedule, connected_devices=connected_devices)

        self._compressor_operating_power = compressor_operating_power
        self._current_temperature = initial_temp
        self._current_outdoor_temperature = None

        self._temperature_max_delta = temp_max_delta  # How much to let the temperature to vary around setpoint

        self._set_point = initial_set_point  # The starting temperature set point

        self._price_to_setpoint = price_to_setpoint  # A list of tuples of (price, setpoint).

        self._compressor_cooling_rate = compressor_cooling_rate

        self._heat_exchange_rate = heat_exchange_rate
        self._last_temperature_update_time = 0.0  # the time the last internal temperature update occurred

        self._compressor_is_on = False
        self._compressor_should_be_on = False

        if temperature_schedule is None:
            raise ValueError("tried to initialize air conditioner without temperature schedule")
        self._temperature_schedule = temperature_schedule
        self.schedule_outdoor_temperature_events(self._temperature_schedule, total_runtime)

    ##
    # Schedules all of the temperature change events each day for the entire duration of the simulation.
    # @param temperature_schedule a list of tuples of (time, temperature) for outdoor temperatures.
    def schedule_outdoor_temperature_events(self, temperature_schedule, total_runtime):
        curr_day = 0  # The current day in seconds
        while curr_day < total_runtime:
            for time, temp in temperature_schedule:
                temperature_event = Event(self.update_outdoor_temperature, temp)
                self.add_event(temperature_event, time + curr_day)
            curr_day += SECONDS_IN_DAY

    ##
    # Given the current price of the device, determine what the current temperature setpoint should be.
    def reassess_setpoint(self):
        if self._price is None:
            return
        new_set_point = self.get_setpoint_from_price(self._price)
        if new_set_point != self._set_point:
            self._set_point = new_set_point
            self._logger.info(self.build_log_notation(
                message="setpoint changed to {}".format(new_set_point), tag="set_point", value=new_set_point))

    ##
    # Returns the setpoint value from the given price by finding the next largest price-setpoint value in the
    # input setpoint dictionary.
    def get_setpoint_from_price(self, price):
        if self._price_to_setpoint is None:
            return self._set_point
        sorted_by_price = sorted(self._price_to_setpoint, key=lambda d: d[0])
        for price_val, setpoint in sorted_by_price:
            if price <= price_val:
                return setpoint
        return sorted_by_price[-1][1]  # Price is higher than all in dictionary. Return the last value.

    ##
    # Adjusts the internal temperature of the a/c based on the indoor/outdoor temperature difference
    def adjust_internal_temperature(self):

        if self._time > self._last_temperature_update_time:
            delta_t = (self._time - self._last_temperature_update_time) / 3600.0  # time difference in hours
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
                self._logger.debug(self.build_log_notation(
                        message="Internal temperature", tag="internal_temperature", value=self._current_temperature))

            self._last_temperature_update_time = self._time

    ##
    # Given the current internal temperature of the air conditioner and the desired setpoint, determine
    # whether the compressor should be on. If the compressor should not be on, turn it off. If it should be,
    # record that so we can request the necessary power in order to turn it on.

    def control_compressor_operation(self):
        if self._set_point is None or not self._in_operation:
            return

        delta = self._current_temperature - self._set_point
        self._logger.debug(self.build_log_notation(
                          message="delta from setpoint: {}".format(delta), tag="delta_t", value=delta))

        if abs(delta) > self._temperature_max_delta:
            if delta > 0 and not self._compressor_is_on:
                # if the current temperature is above the set point and compressor is off, turn it on
                self._logger.debug(self.build_log_notation(
                    message="temp: {}, setpoint: {}, above delta threshold".format(
                        self._current_temperature, self._set_point), tag="above_delta_threshold", value=delta))
                self._compressor_should_be_on = True

            elif delta < 0 and self._compressor_is_on:
                # if current temperature is below the set point and compressor is on, turn it off
                self._logger.debug(self.build_log_notation(
                    message="temp: {}, setpoint: {}, below delta threshold".format(
                        self._current_temperature, self._set_point), tag="below_delta_threshold", value=delta))
                self._compressor_should_be_on = False
                self.turn_off_compressor()

    ##
    # Turns on the compressor.
    def turn_on_compressor(self):
        if self._in_operation:
            self._logger.info(self.build_log_notation(message="compressor_on", tag="compressor_on_off", value=1))
            self._compressor_is_on = True

    ##
    # Turns off the compressor.
    def turn_off_compressor(self):
        self._compressor_is_on = False
        self._logger.info(self.build_log_notation(message="turn off compressor", tag="compressor_on_off", value=0))

    ##
    # Refresh the current outdoor temperature value.
    # @param new_temperature the new outdoor temperature value
    def update_outdoor_temperature(self, new_temperature):
        self._logger.debug(self.build_log_notation(message="new outdoor temperature: {}".format(new_temperature),
                                                   tag="new_temp", value=new_temperature))
        self._current_outdoor_temperature = new_temperature

    ##
    # Air conditioner will shut off compressor whenever device shuts off.
    def end_internal_operation(self):
        if self._compressor_is_on:
            self.turn_off_compressor()

    ##
    # Air conditioner does not have startup behavior
    def begin_internal_operation(self):
        pass

    ##
    # Updates the state of the air conditioner by determining its internal temperature, desired setpoint, and
    # hence desired
    def update_state(self):
        self.adjust_internal_temperature()
        self.reassess_setpoint()
        self.control_compressor_operation()

    ##
    # This air conditioner consumes what it requires to run the compressor if the compressor should be on.
    # @return the amount of power this a/c would like to consume
    def calculate_desired_power_level(self):
        if self._compressor_should_be_on:
            return self._compressor_operating_power
        else:
            return 0.0

    ##
    # When this Air Conditioner receives power, if it is sufficient for its needs it turns the compressor on.
    # Otherwise, if the compressor can no longer operate turn it off.
    def respond_to_power(self, received_power):
        # We didn't get enough power to operate the compressor
        if received_power < self._compressor_operating_power:
            if self._compressor_is_on:
                self._logger.info(self.build_log_notation(
                    message="insufficient power to run compressor", tag="insufficient power", value=received_power))
                self.turn_off_compressor()
        else:
            # If we got enough power and we should be running, turn compressor on
            if not self._compressor_is_on and self._compressor_should_be_on:
                self.turn_on_compressor()

    def device_specific_calcs(self):
        pass


