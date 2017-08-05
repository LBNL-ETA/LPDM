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

"""A battery is a component of a grid controller which serves to balance its inflows and outflows
The Grid Controller thus has complete control over its battery(s), no messages are passed between them
but instead power flows are instantaneous.

Batteries encapsulate this behavior of a Grid Controller:
"""

from enum import Enum


class Battery(object):

    ##
    # Battery charging preference is based on the batteries current state of charge (soc).
    # Discharge indicates it would like to provide power, neutral no preference, charge to receive power.
    class BatteryChargingPreference(Enum):
        DISCHARGE = -1
        NEUTRAL = 0
        CHARGE = 1

    ##
    # Initializes the battery to be contained within a grid controller.
    # @param capacity the maximum charge capacity of the battery. Default 5000 kwh
    # @param starting_soc the state of charge on initialization. Default 50%

    def __init__(self, capacity=5000.0, starting_soc=.5):

        self._charging_preference = self.BatteryChargingPreference.NEUTRAL
        self._preferred_charge_rate = 0 # battery's ideal charge rate, in kW
        self._preferred_discharge_rate = 0 # battery's ideal discharge rate, in kW
        self._max_charge_rate = 0 # largest possible charge rate, in kW
        self._max_discharge_rate = 0 # largest possible discharge rate, in kW
        self._capacity = capacity # energy capacity of the battery, in kWh.
        self._current_charge = starting_soc * capacity
        self._load = 0  # the load on the battery, either in or out, in kW.
        self._sum_charge_kwh = 0.0
        self._time = 0

    def on_power_change(self):
        pass



    def sum_charge_kwh(self):
        """Keep a running total of the energy used for charging"""
        time_diff = self._time - self._last_charge_update_time
        power_level = self.charge_rate() if self._is_charging else 0
        if time_diff > 0 and power_level > 0:
            self._sum_charge_kwh += power_level * (time_diff / 3600.0)
        self._last_charge_update_time = self._time

    def write_calcs(self):
        PowerSource.write_calcs(self)
        self._logger.info(self.build_message(
            message="sum charge_kwh",
            tag="sum_charge_kwh",
            value=self._sum_charge_kwh / 1000.0
        ))


