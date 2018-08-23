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
An implementation of a notebook personal computer EUD.

Use data for MacBook (from 2017) for now.
Its USB-C Power Adapter (29[W]  Model A1540) to get an idea of current flow to the computer
Output 14.5[V] - 2.0[A] or 5.2[V] - 2.4[A]
Use the current value for 14.5[V]: 2.0[A] since it is assumed that the internal battery operates on
12[V]

Power consumption is adjusted changing the brightness of the computer monitor.
However, it is assumed that there is always a fixed power consumption for the rest of the computer,
such as power consumed by CPU.
"""

from Build.Simulation_Operation.support import SECONDS_IN_DAY
from Build.Objects.eud import Eud

class NotebookPersonalComputer(Eud):

    #
    # Default values for internal battery:
    # Use the data for "Battery and Power" for MacBook 2018 for now
    # (https://www.apple.com/macbook/specs/)
    #  "Up to 10 hours wireless web3
    #   Up to 12 hours iTunes movie playback3
    #   Up to 30 days of standby time3
    #   Built-in 41.4-watt-hour lithium-polymer battery
    #   29W USB-C Power Adapter; USB-C power port"
    #
    #   nominal_voltage = 12  # 12[V]
    #   nominal_current = 2  # 2[V] derived from output current of power adapter
    #   capacity = 41.4  # 41.4[Wh] / 12[V] in order to get value in [Ah]
    #
    def __init__(self, device_id, supervisor, total_runtime=SECONDS_IN_DAY, multiday=0,
                 modulation_interval=7200,
                 msg_latency=0, time=0, schedule=None, connected_devices=None, max_operating_power=100.0,
                 power_level_max=1.0, power_level_low=0.2, price_dim_start=0.1, price_dim_end=0.2, price_off=0.3,
                 charging_state_of_charge_intercept = 1.0, charging_price_intercept = 0.6,
                 discharging_state_of_charge_intercept = 1.2, discharging_price_intercept = 0.8,
                 nominal_voltage = 12, nominal_current = 2, capacity = 41.4):
        super().__init__(device_id=device_id, device_type="personal_computer",
                         supervisor=supervisor, total_runtime=total_runtime,
                         multiday=multiday,
                         modulation_interval=modulation_interval, msg_latency=msg_latency, time=time,
                         schedule=schedule, connected_devices=connected_devices)
        self._max_operating_power = max_operating_power  # the device's ideal maximum power usage
        self._power_level_max = power_level_max  # percentage of power level to operate at when price is low
        self._power_level_low = power_level_low  # percent of power level to operate at when price is high.
        self._price_dim_start = price_dim_start  # the price at which to start to lower power
        self._price_dim_end = price_dim_end  # price at which to change to lower_power mode.
        self._price_off = price_off  # price at which to turn off completely
        self._power_consumption_ratio = 0.0  # The percentage of this computer's consumption
        self._on = False  # Whether the light is on

        self._internal_battery = self.Battery(charging_state_of_charge_intercept,
                                              charging_price_intercept,
                                              discharging_state_of_charge_intercept, discharging_price_intercept,
                                              nominal_voltage, nominal_current,
                                              capacity / nominal_voltage)

    ##
    # Calculate the desired power level in based on the price (watts). Algorithm is described in
    # software documentation.
    #
    def calculate_desired_power_level(self):

        desired_power_level_by_battery = self._internal_battery.calculate_desired_power_level(
                                                    self._price)

        # As a start, it is assumed that the computer is always on:
        #if self._in_operation and self._on:
        if self._price <= self._price_dim_start:
            # Operate at maximum capacity when below this threshold
            desired_power_level_by_computer = self._power_level_max * self._max_operating_power
        elif self._price <= self._price_dim_end:
            # Linearly reduce power consumption
            power_reduce_ratio = (self._price - self._price_dim_start) / (self._price_dim_end - self._price_dim_start)
            power_level_reduced = self._power_level_max - ((self._power_level_max - self._power_level_low) * power_reduce_ratio)
            desired_power_level_by_computer = self._max_operating_power * power_level_reduced
        elif self._price <= self._price_off:
            # In this price range operate in low power mode
            desired_power_level_by_computer = self._power_level_low * self._max_operating_power
        else:
            desired_power_level_by_computer = 0.0 # not in operation or price too high.

        desired_power_level = desired_power_level_by_computer + desired_power_level_by_battery
        # Since notebook personal computer doesn't send power to Grid Controller,
        # if the calculated desired_power_level becomes less than 0, it is set to 0.
        if desired_power_level < 0.0:
            desired_power_level = 0.0

        return desired_power_level

    ##
    # Turns the computer "on", and hence begins consuming power.
    def on(self):
        self._on = True
        #self.modulate_power()

    ##
    # Turns the computer "off", and stops consuming power.
    # Since computer is assumed to be always on, this method doesn't do anything.
    def off(self):
        # self._on = False
        # gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
        # for gc in gcs:
        #     self.send_power_message(gc, 0)
        #     self.change_load_in(gc, 0)
        # self.set_power_in(0)
        # self.set_power_out(0)
        pass

    ##
    # @param received_power how much power this notebook personal computer received to operate
    def respond_to_power(self, received_power):
        if received_power > self._max_operating_power:
            self._internal_battery.charge(received_power - self._max_operating_power)
            self._power_consumption_ratio = 1.0
        # Case for keeping minimum power consumption:
        elif (received_power / self._max_operating_power) < self._power_level_low:
            power_deficit = (self._power_level_low - (received_power / self._max_operating_power)) \
                                * self._max_operating_power
            power_that_cannot_be_supplied_by_battery = \
                                self._internal_battery.discharge(power_deficit)
            if power_that_cannot_be_supplied_by_battery > 0:
                # TODO: Implement the mechanism to shutdown the computer due to lack of power
                self._power_consumption_ratio = 0.0
            else:
                self._power_consumption_ratio = self._power_level_low
        else:
            self._power_consumption_ratio = received_power / self._max_operating_power

        self._logger.info(self.build_log_notation(
            message="power consumption ratio changed to {}".format(
                                self._power_consumption_ratio),
            tag="power consumption ratio",
            value=self._power_consumption_ratio
        ))
        self._logger.info(self.build_log_notation(
            message="internal battery state of charge changed to {}".format(
                                self._internal_battery.state_of_charge),
            tag="internal battery state of charge",
            value=self._internal_battery.state_of_charge
        ))

    """The notebook personal computer does not keep track of a dynamic internal state for now.
    """

    ##
    #
    def update_state(self):
        pass

    ##
    #
    def begin_internal_operation(self):
        pass

    ##
    #
    def end_internal_operation(self):
        pass

    ##
    #
    def device_specific_calcs(self):
        pass

    @property
    def power_consumption_ratio(self):
        return self._power_consumption_ratio

    @property
    def internal_battery(self):
        return self._internal_battery

    class Battery(object):

        _state_of_charge = 0.0

        def __init__(self, charging_state_of_charge_intercept, charging_price_intercept,
                     discharging_state_of_charge_intercept, discharging_price_intercept,
                     nominal_voltage, nominal_current, capacity_in_ah):
            self._charging_state_of_charge_intercept = charging_state_of_charge_intercept
            self._charging_price_intercept = charging_price_intercept
            self._discharging_state_of_charge_intercept = discharging_state_of_charge_intercept
            self._discharging_price_intercept = discharging_price_intercept

            self._nominal_voltage = nominal_voltage
            self._nominal_current = nominal_current
            self._capacity_in_ah = capacity_in_ah  # [Ah]

        @property
        def capacity_in_ah(self):
            return self._capacity_in_ah

        @capacity_in_ah.setter
        def capacity_in_ah(self, value):
            self._capacity_in_ah = value

        @property
        def state_of_charge(self):
            return self._state_of_charge

        @state_of_charge.setter
        def state_of_charge(self, value):
            self._state_of_charge = value

        # Note: Simple implementation as a start
        def charge(self, power):
            state_of_charge_change = self._calculate_state_of_charge_change(power)
            if self._state_of_charge + state_of_charge_change <= 1.0:
                self._state_of_charge += state_of_charge_change
            else:
               self._state_of_charge = 1.0

        def discharge(self, power):
            state_of_charge_change = self._calculate_state_of_charge_change(power)
            if self._state_of_charge >= state_of_charge_change:
                self._state_of_charge -= state_of_charge_change
                power_that_cannot_be_supplied = 0.0
                return power_that_cannot_be_supplied
            else:
                self._state_of_charge = 0.0
                power_that_cannot_be_supplied = (state_of_charge_change - self._state_of_charge) * \
                                    (self._capacity_in_ah / 1) * self._nominal_voltage
                return power_that_cannot_be_supplied

        def calculate_desired_power_level(self, price):

            charging_boundary_state_of_charge_for_given_price = \
                                        self._calculate_charging_boundary_state_of_charge(price)
            discharging_boundary_state_of_charge_for_given_price = \
                                        self._calculate_discharging_boundary_state_of_charge(price)

            if self._state_of_charge <= charging_boundary_state_of_charge_for_given_price:
                return self._nominal_voltage * self._nominal_current
            elif self._state_of_charge >= discharging_boundary_state_of_charge_for_given_price:
                # Discharge to supply power to the computer instead of making computer get power
                # from Grid Controller:
                return -(self._nominal_voltage * self._nominal_current)
            else:
                return 0.0

        # Based on the linear equation.
        def _calculate_charging_boundary_state_of_charge(self, price):
            result = -(self._charging_state_of_charge_intercept / self._charging_price_intercept) \
                                             * price + self._charging_state_of_charge_intercept
            if result < 0.0:
                result = 0.0
            elif result > 1.0:
                result = 1.0
            return result

        # Based on the linear equation:
        def _calculate_discharging_boundary_state_of_charge(self, price):
            result = -(self._discharging_state_of_charge_intercept /
                        self._discharging_price_intercept) \
                        * price + self._discharging_state_of_charge_intercept
            if result < 0.0:
                result = 0.0
            elif result > 1.0:
                result = 1.0
            return result

        def _calculate_state_of_charge_change(self, power):
            # Note: Energy is measured in [Wh] thus assuming time has a unit of hour:
            current = power / self._nominal_voltage
            capacity_change = current * 1 # [Ah]
            return capacity_change / self._capacity_in_ah
