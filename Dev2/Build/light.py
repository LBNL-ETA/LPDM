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

from Build.device import Device
from Build.eud import Eud


class Light(Eud):

    def __init__(self, device_id, supervisor, max_operating_power, read_delay=0, time=0, connected_devices=None):
        super().__init__(device_id, "light", supervisor, read_delay=read_delay, time=time,
                         connected_devices=connected_devices)
        self._max_operating_power = max_operating_power  # the device's ideal maximum power usage
        self._power_level_max = 1.0  # percentage of power level to operate at when price is low
        self._power_level_low = 0.2  # percent of power level to operate at when price is high.
        self._price_dim_start = 0.1  # the price at which to start to lower power
        self._price_dim_end = 0.2  # price at which to change to lower_power mode.
        self._price_off = 0.3  # price at which to turn off completely


    ## Will need to implement modulate power, which will involve sending a request message once
    # it determines that it needs a set amount of power.
    # TODO: Is this an EUD level generality?

    def on(self):
        self._logger.info(self.build_message(
            message="turn on device {}".format(self._device_id),
            tag="turn on",
            value=1
        ))
        self.turn_on()
        self.modulate_power()

    def off(self):
        self.turn_off()
        self._logger.info(self.build_message(
            message="turn off device {}".format(self._device_id),
            tag="turn off",
            value=0
        ))

    ##
    # Calculate the desired power level (w) based on the price..
    #
    def calculate_desired_power_level(self):
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
        else:
            return 0.0

    def modulate_power(self):
        power_seek = self.calculate_desired_power_level() - self._power_in
        if power_seek:
            gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
            if len(gcs): # TODO: Make this an allocate request.
                self.send_power_message(gcs[0], -power_seek)  # negative because seeking to receive.
            else:
                self.turn_off()





