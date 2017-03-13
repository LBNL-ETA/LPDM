

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
    Implementation of the Diesel Generator device.
"""
from device.power_source import PowerSource
import logging
import pprint

class DieselGenerator(PowerSource):
    """
        Device implementation of a diesel generator.

        Usage:
            Instantiate the class with a dictionary of configuration options.

            generator = DieselGenerator(configuration_options)

        Attributes:
            _device_name: Name of the device
            _fuel_tank_capacity: Fuel capacity (gallons)
            _fuel_level: Current fuel level (percent)
            _fuel_reserve: Percent of initial value that is goal for having when refuel schedules (%)
            _days_to_refuel: How many days until refuel
            _kwh_per_gallon: Power output of generator (kwh/gallon)
            _time_to_reassess_fuel:  Interval for calculating the trajectory of consumption (seconds)
            _fuel_price_change_rate: Ceiling for fuel price change (%)
            _gen_eff_zero: generator efficiency (%) at zero output
            _gen_eff_100: generator efficiency (%) at 100% output
            _price_reassess_time: interval for reassessing price (seconds)
            _fuel_base_cost: Base cost of fuel ($/gallon)

            _current_fuel_price: current price of fuel ($/W-sec)

            _start_hour_consumption: The start time for tracking the hourly consumption
            _consumption_activity: Array that tracks the changes in consumption
            _consumption_24hr: Keeps track of the last 24 hours of diesel consumption by hour

            _last_fuel_status_time: Time when the last fuel status was calculated
            _target_refuel_time_secs: Time in seconds when the next refuel is expected
            _events: Upcoming events that are to be processed


    """
    def __init__(self, config = None):
        """
        Example:
            generator = DieselGenerator(config)

        Args:
            config (dict): Dictionary of default configuration values

                Valid Keys:

                "fuel_tank_capacity" (float): Capacity of the fuel tank in gallons.
                "fuel_level" (float): The current fuel level expressed as a percentage of the initial value (0 - 100)
                "fuel_reserve" (float): Percent of initial value that is goal for having when refuel schedules (%)
                "days_to_refuel" (int): How many days until refuel
                "kwh_per_gallon" (float): Power output of the generator (kWh/gallon)
                "time_to_reassess_fuel" (int): Interval for calculating the trajectory of consumption (seconds)
                "fuel_price_change_rate" (float): Maximum change amount for a change in fuel price change (%)
                "capacity" (float): the Maximum output capacity (Watts)
                "gen_eff_zero" (float): Generator efficiency at zero output (%)
                "gen_eff_100" (float): Generator efficiency at 100% output (%)
                "price_reassess_time" (int): Interval for reassessing price (seconds)
                "fuel_base_cost" (float): Base cost of fuel ($/gallon)
                "current_fuel_price" (float): The initial price of fuel ($/kWh)
        """
        # call the super constructor
        PowerSource.__init__(self, config)

        # set the properties specific to a diesel generator
        self._fuel_tank_capacity = config.get("fuel_tank_capacity", 100.0)
        self._fuel_level = config.get("fuel_level", 100.0)
        self._fuel_reserve = config.get("fuel_reserve", 20.0)
        self._days_to_refuel = config.get("days_to_refuel", 7)
        self._kwh_per_gallon = config.get("kwh_per_gallon", 36.36)
        self._time_to_reassess_fuel = config.get("time_to_reassess_fuel", 21600)
        self._fuel_price_change_rate = config.get("fuel_price_change_rate", 5.0)
        self._capacity = config.get("capacity", 2000.0)
        self._gen_eff_zero = config.get("gen_eff_zero", 0.0)
        self._gen_eff_100 = config.get("gen_eff_100", 100.0)
        self._price_reassess_time = config.get("price_reassess_time", 3600)
        self._fuel_base_cost = config.get("fuel_base_cost", 5.0)

        self._start_hour_consumption = 0 # time when the last consumption calculation occured
        self._consumption_activity = []    #track the consumption changes for the hour
        self._consumption_24hr = [] # keeps track of the last 24 hours of diesel consumption by hour

        self._last_fuel_status_time = 0
        self._events = []

        self._target_refuel_time_secs = None
        self._base_refuel_time_secs = 0

        self._scarcity_multiplier = 1.0

        self._time_price_last_update = 0

        # load a set of attribute values if a 'scenario' key is present
        if type(config) is dict and 'scenario' in config.keys():
            self.set_scenario(config['scenario'])

    def init(self):
        """Run any initialization functions for the device"""
        # Setup the next events for the device
        self.set_target_refuel_time()
        self.set_next_hourly_consumption_calculation_event()
        self.set_next_reasses_fuel_change_event()
        self.set_next_refuel_event()
        self.calculate_electricity_price()
        self.make_available()
        self.calculate_next_ttie()

    def status(self):
        return {
            "type": "diesel_generator",
            "in_operation": self._in_operation,
            "fuel_price": self._current_fuel_price,
            "power_level": self._power_level,
            "output_capcity": self.current_output_capacity(),
            "generation_rate": self.get_current_generation_rate(),
            "fuel_level": self._fuel_level
        }

    def refresh(self):
        "Refresh the diesel generator."
        self.log_message("Refresh the diesel generator")
        self.remove_refresh_events()
        self.set_target_refuel_time()
        self.set_next_refuel_event()

        self.update_fuel_level()
        self.calculate_electricity_price()
        self.reasses_fuel()
        self.calculate_next_ttie()

    def remove_refresh_events(self):
        "Remove events that need to be recalculated when the device status is refreshed.  For the diesel generator this is just the refuel event."
        next_refuels = []
        for event in self._events:
            if event['operation'] == 'refuel':
                next_refuels.append(event)

        for event in next_refuels:
            self.log_message("Remove event: {}".format(pprint.pformat(event), app_log_level=None))
            self._events.remove(event)

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured (W)"

        if target_device_id == self._device_id:
            self._time = time
            self.log_message(
                "received power change from {}, to {}, new_power = {}".format(source_device_id, target_device_id,  new_power)
            )
            if new_power > 0 and not self.is_on() and self._fuel_level > 0:
                # If the generator is not in operation the turn it on
                self.turn_on()
                self._power_level = new_power
                # calculate the new electricity price
                self.calculate_electricity_price()
                # set to re calculate a new price
                self.set_next_price_change_event()
                self.calculate_next_ttie()
                # store the new power consumption for the hourly usage calculations
                self.log_power_change(time, new_power)
            elif new_power > 0 and self.is_on() and self._fuel_level > 0:
                # power has changed when already in operation
                # store the new power value for the hourly usage calculation
                self.log_message(
                    message="change generator power level ({} to {})".format(self._power_level, new_power),
                    tag="power",
                    value=new_power
                )
                self._power_level = new_power
                self.log_power_change(time, new_power)
                self.calculate_electricity_price()
            elif new_power > 0 and self._fuel_level <= 0:
                if self.is_on():
                    self.turn_off()
                    self._power_level = 0.0
                    self.log_message(
                        message="change generator power",
                        tag="power",
                        value=0
                    )
                self.broadcast_new_power(0.0, target_device_id=self._grid_controller_id)
            elif new_power <= 0 and self.is_on():
                # Shutoff power
                self.turn_off()
                self.log_message(
                    message="change generator power",
                    tag="power",
                    value=0
                )
                self._power_level = 0.0
                self.log_power_change(time, 0.0)
        return

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        return

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self.log_message("DG received new ttie {}".format(new_time))
        self._time = new_time
        self.process_events()
        self.calculate_next_ttie()
        return

    def set_next_hourly_consumption_calculation_event(self):
        "Setup the next event for the calculation of the hourly consumption"
        self._events.append({"time": self._time + 60 * 60, "operation": "hourly_consumption"})
        return

    def set_next_price_change_event(self):
        "Setup the next event for a price change"
        self._events.append({"time": self._time + self._price_reassess_time, "operation": "price"})
        return

    def set_next_reasses_fuel_change_event(self):
        "Setup the next event for reassessing the fuel level"
        if self._time == 0:
            self._events.append({"time": self._time + 60 * 60 * 24, "operation": "reasses_fuel"})
        else:
            self._events.append({"time": self._time + 60 * 60 * 6, "operation": "reasses_fuel"})

        return

    def set_initial_price_event(self):
        """Let all other devices know of the initial price of energy"""
        self._events.append({"time": 0, "operation": "emit_initial_price"})

    def set_initial_capacity_event(self):
        """Let all other devices know of the initial price of energy"""
        self._events.append({"time": 0, "operation": "emit_initial_capacity"})

    def set_next_refuel_event(self):
        self._events.append({"time": self._time + self._days_to_refuel * 3600.0 * 24.0, "operation": "refuel"})

    def log_power_change(self, time, power):
        "Store the changes in power usage"
        self._consumption_activity.append({"time": time, "power": power})

    def process_events(self):
        "Process any events that need to be processed"
        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "price":
                    if self.is_on():
                        self.update_fuel_level()
                        self.calculate_electricity_price()

                    self.set_next_price_change_event()
                    remove_items.append(event)
                elif event["operation"] == "hourly_consumption":
                    self.calculate_hourly_consumption(is_initial_event=True)
                    self.set_next_hourly_consumption_calculation_event()
                    remove_items.append(event)
                elif event["operation"] == "reasses_fuel":
                    self.reasses_fuel()
                    self.set_next_reasses_fuel_change_event()
                    remove_items.append(event)
                elif event["operation"] == "refuel":
                    self.refuel()
                    self.set_next_refuel_event()
                    remove_items.append(event)
                elif event["operation"] == "emit_initial_price":
                    self.calculate_electricity_price()
                    remove_items.append(event)
                elif event["operation"] == "emit_initial_capacity":
                    self.broadcast_new_capacity()
                    remove_items.append(event)

        # remove the processed events from the list
        if len(remove_items):
            for event in remove_items:
                self._events.remove(event)

        return

    def update_fuel_level(self):
        "Update the fuel level"
        kwh_used = 0.0
        interval_start_time = self._time

        # calculate how much energy has been used since the fuel level was last updated
        for item in self._consumption_activity[::-1]:
            if item["time"] < self._last_fuel_status_time:
                time_diff = (interval_start_time - self._last_fuel_status_time) / 3600.0
                kwh_used += item["power"] / 1000.0 * time_diff
                break
            else:
                time_diff = (interval_start_time - item["time"]) / 3600.0
                kwh_used += item["power"] / 1000.0 * time_diff
                interval_start_time = item["time"]

        kwh_per_gallon = self.get_current_generation_rate()
        gallons_used = kwh_used / kwh_per_gallon
        gallons_available = self._fuel_tank_capacity * (self._fuel_level / 100.0)
        new_gallons = gallons_available - gallons_used

        self._last_fuel_status_time = self._time
        new_fuel_level = new_gallons / self._fuel_tank_capacity * 100

        self.log_message(
            message="Fuel level updated",
            tag="fuel_level",
            value=new_fuel_level
        )
        self._fuel_level = new_fuel_level

        if self._fuel_level <= 0:
            self.turn_off()
            self._power_level = 0.0
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)
            self._current_fuel_price = 1e6
            self.broadcast_new_price(self._current_fuel_price, target_device_id=self._grid_controller_id)
        return

    def set_days_to_refuel(self, days_to_refuel):
        "Sets the number of days until refuel"
        self.log_message(
            message="Set days to refuel",
            tag="days_until_refuel",
            value=days_to_refuel
        )

    def get_current_generation_rate(self):
        "Calculates the current generation rate in kwh/gallon"
        return self.get_generation_rate(self._fuel_level)

    def get_generation_rate(self, fuel_level):
        return (self._gen_eff_zero / 100.0 + (self._gen_eff_100 - self._gen_eff_zero) / 100.0 * (fuel_level / 100.0)) * self._kwh_per_gallon

    def get_total_energy_available(self):
        "Get the total energy available in the tank (current fuel tank level in gallons * kwh/gallon). return the value in watt-seconds"
        # return self._fuel_tank_capacity * (self._fuel_level / 100.0) * self.get_current_generation_rate() * (60 * 60 * 1000)
        return self._fuel_tank_capacity * (self._fuel_level / 100.0) * self.get_current_generation_rate()

    def calculate_electricity_price(self):
        "Calculate a new electricity price ($/W-sec), based on instantaneous part-load efficiency of generator"
        if self._fuel_level > 0 and (self.ok_to_calculate_price() or self._time == 0) and (not self._static_price or (self._static_price and self._current_fuel_price is None)):
            if self._current_fuel_price > 1e5:
                self._current_fuel_price = None
            self._time_price_last_update = self._time
            new_price = self._fuel_base_cost / self.get_current_generation_rate() * self._scarcity_multiplier
            if self._current_fuel_price and abs(new_price - self._current_fuel_price) / self._current_fuel_price > (self._fuel_price_change_rate / 100.0):
                new_price = self._current_fuel_price + ((self._current_fuel_price * (self._fuel_price_change_rate / 100.0)) * (1 if new_price > self._current_fuel_price else -1))

            # print("fuel_level = {0}, gen_rate = {1}, price = {2}, base_cost = {3}, raw_calc = {4}".format(self._fuel_level, self.get_current_generation_rate(), new_price, self._fuel_base_cost, self._fuel_base_cost / self.get_total_energy_available()))
            if new_price != self._current_fuel_price:
                self._current_fuel_price = new_price
                self.broadcast_new_price(new_price, target_device_id=self._grid_controller_id)

    def ok_to_calculate_price(self):
        "Check if enough time has passed to recalculate the price"
        return self._time - self._time_price_last_update > self._price_reassess_time

    def get_price(self):
        "Get the current fuel price"
        return self._current_fuel_price

    def calculate_hourly_consumption(self, is_initial_event=False):
        "Calculate and store the hourly consumption, only keeping the last 24 hours"
        total_kwh = 0.0
        interval_start_time = self._time

        # calculate how much energy has been used since the fuel level was last updated
        for item in self._consumption_activity[::-1]:
            if item["time"] < self._start_hour_consumption:
                time_diff = (interval_start_time - self._start_hour_consumption) / 3600.0
                total_kwh += item["power"] / 1000.0 * time_diff
                break
            else:
                time_diff = (interval_start_time - item["time"]) / 3600.0
                total_kwh += item["power"] / 1000.0 * time_diff
                interval_start_time = item["time"]


        # add the hourly consumption to the array
        self._consumption_24hr.append({"time": self._start_hour_consumption, "consumption": total_kwh})

        # set the time the hourly energy sum was last calculated
        self._start_hour_consumption = self._time

        # if we have more than 24 entries, remove the oldest entry
        if len(self._consumption_24hr) > 24:
            self._consumption_24hr.pop(0)

        sum_24hr = 0.0
        for item in self._consumption_24hr:
            sum_24hr += item["consumption"]

        # Log the messages
        self.log_message(
            message="consumption last hour = {}".format(total_kwh),
            tag="consump_hour_kwh",
            value=total_kwh
        )
        self.log_message(
            message="consumption last 24 hours = {}".format(sum_24hr),
            tag="consump_24_hr_kwh",
            value=sum_24hr
        )
        return

    def set_target_refuel_time(self):
        "Set the next target refuel time (sec)"
        self._target_refuel_time_secs = self._base_refuel_time_secs + (self._days_to_refuel * 24 * 60 * 60) if self._days_to_refuel != None else None
        self.log_message(
            message="Set next refuel time",
            tag="set_refuel_time",
            value=self._target_refuel_time_secs
        )

    def refuel(self):
        "Refuel"
        self.log_message(
            message="Refuel the diesel generator, from {} to 100.0".format(self._fuel_level),
            tag="refuel",
            value=1
        )
        self._base_refuel_time_secs = self._time
        self.set_target_refuel_time()

        self._fuel_level = 100.0
        self._scarcity_multiplier = 1.0
        self.calculate_electricity_price()

    def reasses_fuel(self, is_initial_event=False):
        "Calculate the scarcity multiplier"

        # calculate the last 24 hours of fuel consumption
        sum_24hr = 0.0
        for item in self._consumption_24hr:
            sum_24hr += item["consumption"]

        if sum_24hr > 0.0:
            # calculate the average amount of fuel used (fuel use at current time, fuel use when at reserve level)
            gallons_used = sum_24hr / self.get_current_generation_rate()
            gallons_used_at_reserve_level = sum_24hr / self.get_generation_rate(self._fuel_reserve)
            gallons_used_avg = (gallons_used + gallons_used_at_reserve_level) / 2.0

            # gallons when at reserve
            reserve_fuel_gallons = self._fuel_tank_capacity * (self._fuel_reserve / 100.0)

            # gallons currently in tank
            current_fuel_gallons = self._fuel_tank_capacity * (self._fuel_level / 100.0)

            # time in hours when refuelling occurs
            time_until_refuel_hrs = (self._target_refuel_time_secs - self._time) / 3600.0

            # estimate how many gallons would have been used when have reached the refuel time
            total_usage_at_refuel = time_until_refuel_hrs * (gallons_used_avg / 24.0)

            # estimated fuel level at time of refuel
            fuel_level_at_refuel = current_fuel_gallons - total_usage_at_refuel

            # calculate how far we are off from a fuel level at the reserve level
            trajectory = ((fuel_level_at_refuel - reserve_fuel_gallons) / reserve_fuel_gallons) * 100.0

            if trajectory < -10.0:
                # if off by more than 10% then increaes the scarcity multiplier by 5% (fuel level is estimated to be below the reserve_level by 10%)
                self._scarcity_multiplier = self._scarcity_multiplier * 1.05
            elif trajectory > 10.0:
                # decrease the multiplier by 5% if the estimated fuel level would be above the reserve level by 10%
                self._scarcity_multiplier = self._scarcity_multiplier * 0.95
                if self._scarcity_multiplier < 1.0:
                    self._scarcity_multiplier = 1.0

            self.log_message(
                message="reasses fuel - scarcity multiplier",
                tag="scarcity_mult",
                value=self._scarcity_multiplier
            )
        return

    def current_output_capacity(self):
        "Gets the current output capacity (%)"
        return 100.0 * self._power_level / self._capacity

