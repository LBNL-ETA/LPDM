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
from . import message_formatter
from abc import ABCMeta, abstractmethod
import logging


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
    # @param capacity the maximum charge capacity of the battery. Must be a double.
    # @param starting_soc the state of charge on initialization. Default 50%

    def __init__(self, battery_id, price_logic, capacity, max_charge_rate, max_discharge_rate,
                 preferred_charge_rate=-1, preferred_discharge_rate=-1, starting_soc=0.5):

        self._battery_id = battery_id
        self._charging_preference = self.BatteryChargingPreference.NEUTRAL
        self._preferred_charge_rate = preferred_charge_rate if preferred_charge_rate > 0 else max_charge_rate
        self._preferred_discharge_rate = preferred_discharge_rate if preferred_discharge_rate > 0 else max_discharge_rate
        self._max_charge_rate = max_charge_rate  # largest possible charge rate, in kW
        self._max_discharge_rate = max_discharge_rate  # largest possible discharge rate, in kW
        self._capacity = capacity  # energy capacity of the battery, in kWh.
        self._current_soc = starting_soc
        self._load = 0  # the load on the battery, either charge (positive) or discharge (negative), in w.
        self._price = 0  # informed of price by the grid controller on their communications.
        self._price_moving_average = 0  # total moving average of the price, weighted by time that price was maintained
        self._hourly_prices = []  # TODO: Rename this to regular prices.
        self._hourly_moving_price = 0  # battery's hourly moving average of price, weighted by time of that price
        self._time = 0  # battery's local time, updated by grid controller.
        self._last_update_time = 0  # time of last battery update from grid controller
        self.sum_charge_wh = 0.0
        self.sum_discharge_wh = 0.0
        self._logger = logging.getLogger("lpdm")  # Setup logging

        if price_logic == 'hourly_preference':
            self._price_logic = BatteryPriceLogicA()
        elif price_logic == 'moving_average':
            self._price_logic = BatteryPriceLogicB()
        else:
            raise ValueError("tried to set up battery with an invalid price logic")

    ##
    # Adds a new load to the battery
    # @param new_load the load to add
    def get_load(self):
        return self._load

    ##
    # Returns the value of the current batteries charging preference (1 if discharge, 0 if neutral, -1 if discharge)
    def get_charging_preference(self):
        return self._charging_preference.value

    ##
    # Based on the current state of charge determine what the optimal charge rate for the battery is.
    def get_desired_power(self):
        if self._charging_preference.value == 1:
            return self._preferred_charge_rate
        elif self._charging_preference.value == -1:
            return -self._preferred_discharge_rate
        else:
            return 0

    def get_preferred_charge_rate(self):
        return self._preferred_charge_rate

    def get_preferred_discharge_rate(self):
        return self._preferred_discharge_rate

    ##
    # Adds a new load to the battery. Call update state first to ensure valid state of charge
    # and to update charging calculations before modification.
    # @param extra_load the load to add from battery's perspective (positive charge, negative discharge)
    # @param return whatever value was added to the battery's load.
    def add_load(self, extra_load):
        if self._current_soc <= 0 and extra_load < 0:
            return 0  # don't discharge when too low
        if self._current_soc >= 1.0 and extra_load > 0:
            return 0  # don't charge when too high
        old_load = self._load
        self._load += extra_load
        self._load = max(self._load, -self._max_discharge_rate)  # don't add a load to exceed charge rate.
        self._load = min(self._load, self._max_charge_rate)
        return self._load - old_load


    ##
    # Updates the state of charge and power levels of the battery reflecting current time.
    # @param the time to update the battery's local time to
    # @param price the local price of the associated grid controller
    # @param average price information on the average price of the grid controller
    # @param hourly prices information on the hourly prices of the grid controller
    #
    def update_state(self, time, price, average_price, hourly_prices):
        self._time = time
        self._price = price
        self._price_moving_average = average_price
        self._hourly_prices = hourly_prices
        time_diff = time - self._last_update_time

        if time_diff > 0:
            prev_soc = self._current_soc
            power_change = self._load * (time_diff / 3600.0)  # change in battery power level since last update
            new_charge_amt = (prev_soc * self._capacity) + power_change
            self._current_soc = new_charge_amt / self._capacity

            # TODO: self.recalc_charge_preference()
            if power_change > 0:
                self.sum_charge_wh += power_change
            elif power_change < 0:
                self.sum_discharge_wh -= power_change

        self._last_update_time = self._time

    ##
    #
    # @param price_stat the representative statistic to use to calculate it?
    def recalc_charge_preference(self):

        if self._price_logic.issubclass(BatteryPriceLogicA):
            self._charging_preference = self._price_logic.calc_charge_preference(self._current_soc, self._price,
                                                                                 self._hourly_prices)
        elif self._price_logic.issubclass(BatteryPriceLogicB):
            self._charging_preference = self._price_logic.calc_charge_preference(self._current_soc, self._price,
                                                                                 self._price_moving_average)

        self._logger.info(self.build_battery_log_notation(
            "charging preference changed to {}".format(self._charging_preference),
            value=self._charging_preference.value))

    # _____________________________________________________ #
    ##
    # Builds a logging message for this battery, always including information about its state of charge and battery
    # preference.
    # @param message the message to add to logger
    # @param value the value add to the logger

    # @return a formatted string to include in the logger

    def build_battery_log_notation(self, message="", value=None):
        """Build the battery log message string"""
        return message_formatter.build_log_msg(
            time_seconds=self._time,
            message=message,
            tag="current soc : {}, current charge pref: {}".format(self._current_soc, self._charging_preference),
            value=value,
            device_id=self._battery_id
        )


"""
Class to determine the battery's charging preference, based on its current state of charge, current price, 
and price history. 
"""


class BatteryPriceLogic(metaclass=ABCMeta):

    ##
    # Determines the charge preference for this battery based on input parameters of current charge,
    # current price, and a measure of the price history of the battery for the last 24 hours.
    @abstractmethod
    def calc_charge_preference(self, current_soc, current_price, price_history):
        pass


##
# Battery price logic class which utilizes the average past 24 hourly prices to determine the optimal "threshold price"
# which influences when a battery prefers to discharge or charge given its current local price.

class BatteryPriceLogicA(BatteryPriceLogic):

    def __init__(self, starting_price=0.1):
        self._price_threshold_charge = starting_price * 1.1
        self._price_threshold_discharge = starting_price * 0.9

    def calc_average_price(self, price_history):
        sum_price = 0
        for price in price_history:
            sum_price += price
        return sum_price / len(price_history)

    ##
    # Method to calculate the price thresholds which help determine the battery's charging preference.
    # Interprets the past 24 hours average price and sets thresholds relative to the minimum, average,
    # and maximum prices.
    #
    def adjust_price_thresholds(self, current_soc, price_history):
        avg_price = self.calc_average_price(price_history)
        min_price = min(price_history)
        max_price = max(price_history)

        price_threshold_discharge = avg_price * 1.10
        price_threshold_charge = avg_price * 0.90

        if current_soc >= 0.5:
            # decrease the threshold to discharge and charge based on excess level of charge
            soc_ratio = (current_soc - 0.5) / 0.5
            price_adjustment = (max_price - price_threshold_discharge) * soc_ratio
            price_threshold_discharge -= max(price_adjustment, 0)
            price_threshold_charge -= max(price_adjustment, 0)

        else:
            # increase the threshold to charge and discharge based on deficit level of charge
            soc_ratio = (0.5 - current_soc) / 0.5
            price_adjustment = (price_threshold_charge - min_price) * soc_ratio
            price_threshold_discharge += max(price_adjustment, 0)
            price_threshold_charge += max(price_adjustment, 0)

        self._price_threshold_charge = price_threshold_charge
        self._price_threshold_discharge = price_threshold_discharge

    ##
    # Calculates the battery's charging preference based on current price in relation to the calculated
    #  price thresholds and absolute charge levels.
    def calc_charge_preference(self, current_soc, current_price, price_history):
        self.adjust_price_thresholds(current_soc, price_history)
        if current_soc >= 0.5:
            if current_soc >= 0.8 or current_price >= self._price_threshold_discharge:
                return Battery.BatteryChargingPreference.DISCHARGE
            else:
                return Battery.BatteryChargingPreference.NEUTRAL
        else:
            if current_soc <= .2 or current_price <= self._price_threshold_charge:
                return Battery.BatteryChargingPreference.CHARGE
            else:
                return Battery.BatteryChargingPreference.NEUTRAL


##
# Battery price logic class which uses the battery's average price over
# its entire runtime to determine the desired upper and lower charging thresholds.
#

class BatteryPriceLogicB(BatteryPriceLogic):

    def __init__(self, starting_price=0.1):
        self._price_threshold_charge = starting_price * 1.5
        self._price_threshold_discharge = starting_price * 0.66

    ##
    # Sets the thresholds which help determine the battery charging preference, based on direct comparison to
    # the average.
    #
    def adjust_price_thresholds(self, moving_avg_price):

        self._price_threshold_discharge = moving_avg_price * 1.50
        self._price_threshold_charge = moving_avg_price * 0.66

    ##
    # Calculates the battery's charging preference based on current price in relation to the calculated
    #  price thresholds and absolute charge levels.
    def calc_charge_preference(self, current_soc, current_price, price_history):
        self.adjust_price_thresholds(price_history)
        if current_soc >= 0.5:
            if current_soc >= 0.8 or current_price >= self._price_threshold_discharge:
                return Battery.BatteryChargingPreference.DISCHARGE
            else:
                return Battery.BatteryChargingPreference.NEUTRAL
        else:
            if current_soc <= .2 or current_price <= self._price_threshold_charge:
                return Battery.BatteryChargingPreference.CHARGE
            else:
                return Battery.BatteryChargingPreference.NEUTRAL













