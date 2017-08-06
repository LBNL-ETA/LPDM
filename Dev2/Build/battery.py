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
    # @param capacity the maximum charge capacity of the battery. Default 5000 kwh. Must be a double.
    # @param starting_soc the state of charge on initialization. Default 100%

    def __init__(self, price_logic, capacity=5000.0, starting_soc=1.0, max_charge_rate=10000, max_discharge_rate=10000):

        self._charging_preference = self.BatteryChargingPreference.NEUTRAL
        self._price_logic = price_logic
        self._min_soc = 0.2
        self._max_soc = 0.8
        self._preferred_charge_rate = max_charge_rate # temporary. Will be distinct value.
        self._preferred_discharge_rate = max_discharge_rate # temporary. Will be distinct value.
        self._max_charge_rate = max_charge_rate  # largest possible charge rate, in kW
        self._max_discharge_rate = max_discharge_rate  # largest possible discharge rate, in kW
        self._capacity = capacity  # energy capacity of the battery, in kWh.
        self._current_soc = starting_soc
        self._load = 0  # the load on the battery, either charge (negative) or discharge (positive), in kW.
        self._sum_charge_kwh = 0.0
        self._price = 0  # informed of price by the grid controller on their communications.
        self._time = 0
        self._last_charge_update_time = 0

    ##
    # Adds a new load to the battery
    # @param new_load the load to add
    def get_load(self):
        return self._load

    ##
    # Adds a new load to the battery
    # @param new_load the load to add
    # @param return whatever value was added to the battery's load.
    def add_load(self, new_load):
        old_load = self._load
        self._load += new_load
        self._load = min(self._load, self._max_discharge_rate) # don't add a load to exceed charge rate.
        self._load = max(self._load, -self._max_charge_rate)
        return self._load - old_load

    ##
    # Updates the state of charge and power levels of the battery reflecting current time.
    # @param the time to update the battery's local time to
    # @param price the local price of the associated grid controller
    #
    def update_state(self, time, price):
        self._time = time
        self._price = price
        time_diff = time - self._last_charge_update_time
        if time_diff > 0:
            prev_soc = self._current_soc
            power_change = -self._load * (time_diff / 3600.0)
            new_charge_amt = (prev_soc * self._capacity) + power_change
            self._current_soc = new_charge_amt / self._capacity

            self.recalc_charge_preference()
            if power_change > 0:
                self._sum_charge_kwh += power_change

    def recalc_charge_preference(self):
        self._charging_preference = self._price_logic.preference(self._current_soc, self._price)
        #TODO: What actually is this function? Logic?





