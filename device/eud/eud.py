

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
    Implementation of a general EUD device
"""
from device.device import Device
import logging

class Eud(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "eud"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "EUD")

        # max power - set default to 100 watts unless different value provided in configuration
        # operate at max_power_output unless price > 'price_dim'
        self._max_power_output = config.get("max_power_output", 100.0)

        # the price (c/kWh) at which to begin dimming down the power
        # when price > 'price_dim_start' and price < 'price_dim_end', linearly dim down to power level (%) set at 'power_level_low' of power at 'price_dim_end'
        self._price_dim_start = config.get("price_dim_start", 0.3)

        # the price ($/kWh) at which to stop dimming the power output
        # when price > price_dim_end and price < price_off, set to power_level_low
        self._price_dim_end = config.get("price_dim_end", 0.7)

        # the price ($/kWh) at which to turn off the power completeley
        self._price_off = config.get("price_off", 0.9)

        # the max operating power level (%)
        # self._power_level_max = float(config["power_level_max"]) if type(config) is dict and "power_level_max" in config.keys() else 100.0
        self._power_level_max = 100.0

        # the power level (%) to dim down to when price between price_dim and price_off
        # the low operating power level
        self._power_level_low = config.get("power_level_low", 20.0)

        # _schedule_array is the raw schedule passed in
        # _dail_y_schedule is the parsed schedule used by the device to schedule events
        self._schedule_array = config["schedule"] if type(config) is dict and config.has_key("schedule") else None
        self._daily_schedule = self.parse_schedule(self._schedule_array) if self._schedule_array else None

        self._power_level = 0.0

        # set the units
        self._units = 'W'

        # load a set of attribute values if a 'scenario' key is present
        if type(config) is dict and 'scenario' in config.keys():
            self.set_scenario(config['scenario'])

    def status(self):
        return {
            "type": "eud",
            "name": self._device_name,
            "in_operation": self._in_operation,
            "power_level": self._power_level,
            "fuel_price": self._price
        }

    def refresh(self):
        "Refresh the eud. For a basic eud this means resetting the operation schedule."
        self._ttie = None
        self._next_event = None
        self._events = []
        self._daily_schedule = self.parse_schedule(self._schedule_array) if self._schedule_array else None

        # turn on/off the device based on the updated schedule
        should_be_in_operation = self.should_be_in_operation()

        if should_be_in_operation and not self._in_operation:
            self.turn_on()
        elif not should_be_in_operation and self._in_operation:
            self.turn_off()

        self.calculate_next_ttie()

    def should_be_in_operation(self):
        """determine if the device should be operating when a refresh event occurs"""

        current_time_of_day_seconds = self.time_of_day_seconds()
        operating = False
        for item in self._daily_schedule:
            if  item['time_of_day_seconds'] > current_time_of_day_seconds:
                break
            else:
                operating = True if item['operation'] == 1 else False
        return operating

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turn_off()
        return

    def current_schedule_value(self):
        current_time_of_day_seconds = self.time_of_day_seconds()
        res = None
        for schedule_pt in self._daily_schedule:
            if schedule_pt["time_of_day_seconds"] <= current_time_of_day_seconds:
                res = schedule_pt["operation"]
        if not res:
            res = self._daily_schedule[-1]["operation"]
        return res

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self._time = time
            if new_price != self._price:
                self._price = new_price
                self.log_message(
                    message="new price",
                    tag="price",
                    value=new_price
                )
            if self.current_schedule_value():
                self.set_power_level()
            return

    def on_time_change(self, new_time):
        "Receives message when a time change has occured"
        self._time = new_time
        self.process_event()
        self.calculate_next_ttie()
        return

    def force_on(self, time):
        if not self._in_operation:
            self._time = time
            self.turn_on()

    def force_off(self, time):
        if self._in_operation:
            self._time = time
            self.turn_off()

    def turn_on(self):
        "Turn on the device"
        if not self._in_operation:
            self._in_operation = True
            self.log_message(
                message="turn on eud",
                tag="on/off",
                value=1
            )
            self.set_power_level()

    def turn_off(self):
        "Turn off the device"

        if self._in_operation:
            self._power_level = 0.0
            self._in_operation = False
            self.log_message(
                message="turn off eud",
                tag="on/off",
                value=0
            )
            self.log_message(
                message="Power level {}".format(self._power_level),
                tag="power",
                value=self._power_level
            )

    def process_event(self):
        if (self._next_event and self._time == self._ttie):
            if self._in_operation and self._next_event["operation"] == 0:
                self.turn_off()
                self.broadcast_new_power(0.0, target_device_id=self._grid_controller_id)
            elif not self._in_operation and self._next_event["operation"] == 1:
                self.set_power_level()

            self.calculate_next_ttie()

    def calculate_next_ttie(self):
        "Override the base class function"
        if type(self._daily_schedule) is list:
            current_time_of_day_seconds = self.time_of_day_seconds()
            new_ttie = None
            next_event = None
            for item in self._daily_schedule:
                if item['time_of_day_seconds'] > current_time_of_day_seconds:
                    new_ttie = int(self._time / (24 * 60 * 60)) * (24 * 60 * 60) + item['time_of_day_seconds']
                    next_event = item
                    break

            if not new_ttie:
                for item in self._daily_schedule:
                    if item['time_of_day_seconds'] > 0:
                        new_ttie = int(self._time / (24.0 * 60.0 * 60.0)) * (24 * 60 * 60) + (24 * 60 * 60) + item['time_of_day_seconds']
                        next_event = item
                        break

            if new_ttie != self._ttie:
                self._next_event = next_event
                self._ttie = new_ttie
                self.broadcast_new_ttie(new_ttie)

    def parse_schedule(self, schedule):
        if type(schedule) is list:
            return self.load_array_schedule(schedule)

    def load_array_schedule(self, schedule):
        if type(schedule) is list:
            parsed_schedule = []
            for (task_time, task_operation) in schedule:
                task_operation = int(task_operation)
                if len(task_time) != 4 or task_operation not in (0,1):
                    raise Exception("Invalid schedule definition ({0}, {1})".format(task_time, task_operation))
                parsed_schedule.append({"time_of_day_seconds": (int(task_time[0:2]) * 60 * 60 + int(task_time[2:]) * 60), "operation": task_operation})
            return parsed_schedule


    # eud specific methods
    def set_power_level(self):
        "Set the power level for the eud (W).  If the energy consumption has changed then broadcast the new power usage."

        new_power = self.calculate_new_power_level()

        if new_power != self._power_level:
            self._power_level = new_power

            if self._power_level == 0 and self._in_operation:
                self.turn_off()

            elif self._power_level > 0 and not self._in_operation:
                self.turn_on()
            else:
                self.adjust_hardware_power()

            self.broadcast_new_power(new_power, target_device_id=self._grid_controller_id)

    def adjust_hardware_power(self):
        "Override this method to tell the hardware to adjust its power output"
        return None

    def calculate_new_power_level(self):
        "Set the power level of the eud"
        if self._static_price:
            return self._max_power_output
        else:
            if self._price <= self._price_dim_start:
                return self._max_power_output
            elif self._price <= self._price_dim_end:
                return self.interpolate_power()
            elif self._price <= self._price_off:
                return self.get_power_level_low()
            else:
                return 0.0

    def get_power_level_low(self):
        """calculate the lowest operating power output"""
        return self._max_power_output * (self._power_level_low / 100.0)

    def interpolate_power(self):
        "Calculate energy consumption for the eud (in this case a linear interpolation) when the price is between price_dim_start and price_dim_end."
        power_reduction_ratio = (self._price - self._price_dim_start) / (self._price_dim_end - self._price_dim_start)
        power_level_percent = self._power_level_max - (self._power_level_max - self._power_level_low) * power_reduction_ratio
        return self._max_power_output * power_level_percent / 100.0


