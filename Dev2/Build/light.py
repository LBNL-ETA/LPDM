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
An implementation of a light EUD. The light functions such that

"""

from Build.device import Device, SECONDS_IN_DAY
from Build.eud import Eud

# TODO: On and Off to replace the current turn_on, turn_off functions in the input.


class Light(Eud):

    def __init__(self, device_id, supervisor, total_runtime=SECONDS_IN_DAY, multiday=0, modulation_interval=7200,
                 msg_latency=0, time=0, schedule=None, connected_devices=None, max_operating_power=100.0,
                 power_level_max=1.0, power_level_low=0.2, price_dim_start=0.1, price_dim_end=0.2, price_off=0.3):
        super().__init__(device_id=device_id, device_type="light", supervisor=supervisor, total_runtime=total_runtime,
                         multiday=multiday,
                         modulation_interval=modulation_interval, msg_latency=msg_latency, time=time,
                         schedule=schedule, connected_devices=connected_devices)
        self._max_operating_power = max_operating_power  # the device's ideal maximum power usage
        self._power_level_max = power_level_max  # percentage of power level to operate at when price is low
        self._power_level_low = power_level_low  # percent of power level to operate at when price is high.
        self._price_dim_start = price_dim_start  # the price at which to start to lower power
        self._price_dim_end = price_dim_end  # price at which to change to lower_power mode.
        self._price_off = price_off  # price at which to turn off completely
        self._brightness = 0.0  # The percentage of this device's peak brightness, depending on percent of operating pwr
        self._on = False  # Whether the light is on

    ##
    # Calculate the desired power level in based on the price (watts)
    #
    def calculate_desired_power_level(self):
        if self._in_operation and self._on:
            if self._price <= self._price_dim_start:
                return self._power_level_max * self._max_operating_power
            elif self._price <= self._price_dim_end:
                # Linearly reduce power consumption
                power_reduce_ratio = (self._price - self._price_dim_start) / (self._price_dim_end - self._price_dim_start)
                power_level_reduced = self._power_level_max - (
                                     (self._power_level_max - self._power_level_low) * power_reduce_ratio)
                return self._max_operating_power * power_level_reduced

            elif self._price <= self._price_off:
                return self._power_level_low * self._max_operating_power
        return 0.0  # not in operation or price too high.

    ##
    # Turns the light "on", and hence begins consuming power. Does not affect whether device is in operation and can
    # receive messages, only power consumption.
    def on(self):
        self._on = True
        self.modulate_power()

    ##
    # Turns the light "off", and stops consuming power. Does not affect this device's ability to receive messages,
    # and it remains in operation even when off.
    def off(self):
        self._on = False
        gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
        for gc in gcs:
            self.send_power_message(gc, 0)
            self.change_load_in(gc, 0)
        self.set_power_in(0)
        self.set_power_out(0)

    # TODO: Make it so that this device changes its brightness accordingly.
    def respond_to_power(self, received_power):
        self._brightness = received_power / self._max_operating_power
        self._logger.info(self.build_log_notation(
            message="brightness changed to {}".format(self._brightness),
            tag="brightness",
            value=self._brightness
        ))

    """The light does not keep track of a dynamic internal state -- it is just either on or off with its power level
    determining its brightness. Hence, does not perform other EUD functions corresponding its dynamic internal state"""

    ##
    # Light does not change dynamic state
    def update_state(self):
        pass

    ##
    # Light does not have a dynamic internal operation.
    def begin_internal_operation(self):
        pass

    ##
    # Light does not have a dynamic internal operation.
    def end_internal_operation(self):
        pass

    ##
    # Light does not have extra calculations beyond power consumption.
    def device_specific_calcs(self):
        pass



