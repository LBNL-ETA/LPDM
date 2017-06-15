

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
from device.base.device import Device
import logging

class Eud(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)

        self._device_type = "eud"
        # set the properties for an end-use device
        self._device_name = config.get("device_name", "EUD")

        # the price (c/kWh) at which to begin dimming down the power
        # when price > 'price_dim_start' and price < 'price_dim_end', linearly dim down to power level (%) set at 'power_level_low' of power at 'price_dim_end'
        self._price_dim_start = config.get("price_dim_start", 0.1)

        # the price ($/kWh) at which to stop dimming the power output
        # when price > price_dim_end and price < price_off, set to power_level_low
        self._price_dim_end = config.get("price_dim_end", 0.2)

        # the price ($/kWh) at which to turn off the power completeley
        self._price_off = config.get("price_off", 0.3)

        # fixed power output: no interpolation  of power output based on price
        self._constant_power_output = config.get("constant_power_output", False)

        # the max operating power level (%)
        # self._power_level_max = float(config["power_level_max"]) if type(config) is dict and "power_level_max" in config.keys() else 100.0
        self._power_level_max = 100.0

        # the power level (%) to dim down to when price between price_dim and price_off
        # the low operating power level
        self._power_level_low = config.get("power_level_low", 20.0)

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

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._logger.debug(self.build_message(
            message="on_power_change",
            tag="receive_power",
            value=new_power
        ))
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turn_off()

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        """A device has changed its capacity, check if the eud should be in operation"""
        self._time = time
        if not self._in_operation and self.should_be_in_operation():
            self._logger.debug(
                self.build_message(
                    message="eud should be on",
                    tag="capacity_change_on",
                    value=1
                )
            )
            self.turn_on()

    # def current_schedule_value(self):
        # """Is the device scheduled to be on?"""
        # current_time_of_day_seconds = self.time_of_day_seconds()
        # res = None
        # for schedule_pt in self._daily_schedule:
            # if schedule_pt["time_of_day_seconds"] <= current_time_of_day_seconds:
                # res = schedule_pt["operation"]
        # if not res:
            # res = self._daily_schedule[-1]["operation"]
        # return res

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price and target_device_id == self._device_id:
            self._time = time
            if new_price != self._price:
                self._logger.debug(
                    self.build_message(
                        message="new price",
                        tag="receive_price",
                        value=new_price
                    )
                )
                self.set_price(new_price)
                self.adjust_power_output()
                # if the device is in operation, check any dimming calculations to adjust power if needed
            # TODO: fix this part, which turns on the device if it is scheduled to be on
            # if self.current_schedule_value():
                # self.set_power_level()
            # return

    def on_time_change(self, new_time):
        "Receives message when a time change has occured"
        self._time = new_time
        self.process_events()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def force_on(self, time):
        if not self._in_operation:
            self._time = time
            self.turn_on()

    def force_off(self, time):
        if self._in_operation:
            self._time = time
            self.turn_off()

    def process_events(self):
        "Process any events that need to be processed"
        Device.process_events(self)

        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "off":
                    if self._in_operation:
                        self.turn_off()
                    remove_items.append(event)
                    self._current_event = event
                elif event.value == "on" and not self._in_operation:
                    if not self._in_operation:
                        self.turn_on()
                    remove_items.append(event)
                    self._current_event = event

        # remove the processed events from the list
        if len(remove_items):
            for event in remove_items:
                self._events.remove(event)

    def adjust_power_output(self):
        """Adjust the power output of the device, if necessary (ie price has changed and need to adjust power output)"""
        if self._in_operation:
            new_power = self.calculate_power_level()
            if self._power_level != new_power:
                self.set_power_level(new_power)
                self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)


    # def calculate_next_ttie(self):
        # """get the next scheduled task from the schedule and find the next ttie"""
        # # need to have a schedule set up
        # if self._scheduler:
            # next_task = self._scheduler.get_next_scheduled_task(self._time)

            # if next_task and (self._next_event is None or self._ttie != next_task.ttie or self._next_event.value != next_task.value):
                # self._logger.info(
                    # self.build_message(
                        # message="schedule event {}".format(next_task),
                        # tag="scheduled_event"
                    # )
                # )
                # self._next_event = next_task
                # self._ttie = next_task.ttie
                # self.broadcast_new_ttie(self._ttie)

    # eud specific methods
    def adjust_hardware_power(self):
        "Override this method to tell the hardware to adjust its power output"
        return None

    def calculate_power_level(self):
        "Set the power level of the eud"
        if self._static_price or self._constant_power_output:
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



