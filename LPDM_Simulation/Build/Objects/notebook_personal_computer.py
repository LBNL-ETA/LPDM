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

    NOMINAL_DC_INPUT_VOLTAGE = 12

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
        self._brightness = 0.0  # The percentage of this computer monitor's peak brightness,
                                # depending on percent of operating pwr
        self._on = False  # Whether the light is on

        self._internal_battery = self.Battery(charging_state_of_charge_intercept,
                                              charging_price_intercept,
                                              discharging_state_of_charge_intercept, discharging_price_intercept,
                                              nominal_voltage, nominal_current, capacity)

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

        return desired_power_level_by_computer + desired_power_level_by_battery

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
    # The light modulates its brightness based on how much power is received.
    # Brightness is ratio of received power to maximum operating power.
    # @param received_power how much power this light received to operate
    def respond_to_power(self, received_power):
        self._brightness = received_power / self._max_operating_power
        self._logger.info(self.build_log_notation(
            message="brightness changed to {}".format(self._brightness),
            tag="brightness",
            value=self._brightness
        ))

        if received_power > self._max_operating_power:
            self._internal_battery.charge(received_power - self._max_operating_power)

    """The light does not keep track of a dynamic internal state -- it is just either on or off with its power level
    determining its brightness. Hence, does not perform other EUD functions corresponding its dynamic internal state"""

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
    def internal_battery(self):
        return self._internal_battery

    class Battery(object):

        _state_of_charge = 0.0

        def __init__(self, charging_state_of_charge_intercept, charging_price_intercept,
                     discharging_state_of_charge_intercept, discharging_price_intercept,
                     nominal_voltage, nominal_current, capacity):
            self._charging_state_of_charge_intercept = charging_state_of_charge_intercept
            self._charging_price_intercept = charging_price_intercept
            self._discharging_state_of_charge_intercept = discharging_state_of_charge_intercept
            self._discharging_price_intercept = discharging_price_intercept

            self._nominal_voltage = nominal_voltage
            self._nominal_current = nominal_current
            self._capacity_in_ah = capacity / nominal_voltage  # 41.4[Wh] / 12[V]
                                                               # in order to get value in [Ah]

        @property
        def capacity(self):
            return self._capacity

        @capacity.setter
        def capacity(self, value):
            self._capacity = value

        @property
        def state_of_charge(self):
            return self._state_of_charge

        @state_of_charge.setter
        def state_of_charge(self, value):
            self._state_of_charge = value

        # Note: Simple implementation as a start
        def charge(self, power):
            # Note: Energy is measured in [Wh] thus assuming time has a unit of hour:
            current = power / NotebookPersonalComputer.NOMINAL_DC_INPUT_VOLTAGE
            capacity_change = current * 1 # [Ah]
            state_of_charge_change = capacity_change / self._capacity
            if self._state_of_charge + state_of_charge_change <= 1.0:
                self._state_of_charge += state_of_charge_change
            else:
               self._state_of_charge = 1.0

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
