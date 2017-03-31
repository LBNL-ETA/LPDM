

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
    Defines the base class for TuG system components.
"""
import os
import random
import logging
import pprint
import datetime
import json
from notification import NotificationReceiver, NotificationSender
from simulation_logger import message_formatter
# getting an error when trying to import using the absolute path (device.scheduler)
# so used a relative path import
from ...scheduler import Scheduler

from supervisor.lpdm_event import LpdmTtieEvent, LpdmPowerEvent, LpdmPriceEvent, LpdmKillEvent, \
    LpdmConnectDeviceEvent, LpdmAssignGridControllerEvent, LpdmRunTimeErrorEvent, \
    LpdmCapacityEvent

class Device(NotificationReceiver, NotificationSender):
    """
        Base class for TuG system components.

        Usage:
            To create a new device, define a new class that inherits from the Device class.

        Requirements:
            Must override the following methods:
                on_power_change
                on_price_change
                calculate_next_ttie

            Callbacks:
                If the device needs to broadcast changes in power, price, or time, the appropriate callback must be passed into the constructor in the configuration parameter:
                    broadcast_new_power,
                    broadcast_new_price,
                    broadcast_new_ttie
    """
    def __init__(self, config):
        self._device_id = config.get("device_id")
        self._device_name = config.get("device_name", "device")
        self._device_type = config.get("device_type")
        self._uuid = config.get("uuid", None)
        self._price = config.get("price", 0.0)
        self._static_price = config.get("static_price", False)
        self._grid_controller_id = config.get("grid_controller_id", None)
        self._max_power_output = config.get("max_power_output", 0.0)

        # _schedule_array is the raw schedule passed in
        # _dail_y_schedule is the parsed schedule used by the device to schedule events
        self._scheduler = None
        self._schedule_array = config.get("schedule", None)
        self._events = []
        self._current_event = None

        self._power_level = 0.0
        self._time = 0
        self._units = None
        self._in_operation = False
        self._ttie = None
        self._current_capacity = None

        self._broadcast_new_price_callback = config["broadcast_new_price"] if type(config) is dict and  "broadcast_new_price" in config.keys() and callable(config["broadcast_new_price"]) else None
        self._broadcast_new_power_callback = config["broadcast_new_power"] if type(config) is dict and "broadcast_new_power" in config.keys() and callable(config["broadcast_new_power"]) else None
        self._broadcast_new_ttie_callback = config["broadcast_new_ttie"] if type(config) is dict and "broadcast_new_ttie" in config.keys() and callable(config["broadcast_new_ttie"]) else None
        self._broadcast_new_capacity_callback = config["broadcast_new_capacity"] if type(config) is dict and "broadcast_new_capacity" in config.keys() and callable(config["broadcast_new_capacity"]) else None

        # Setup logging
        self._logger = logging.getLogger("lpdm")

        self._logger.info(
            self.build_message("initialized device #{} - {}".format(self._uuid, self._device_type))
        )

    def init(self):
        """Run any initialization functions for the device"""
        self.setup_schedule()
        self.calculate_next_ttie()

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def setup_schedule(self):
        """Setup the schedule if there is one"""
        if type(self._schedule_array) is list:
            self._scheduler = Scheduler(self._schedule_array)
            self._scheduler.parse_schedule()

    def assign_grid_controller(self, grid_controller_id):
        """set the grid controller for the device"""
        self._logger.info(
            self.build_message("attach device to GC {}".format(grid_controller_id))
        )
        self._grid_controller_id = grid_controller_id

    def finish(self):
        "Gets called at the end of the simulation"
        pass

    def uuid(self):
        return self._uuid;

    def device_name(self):
        return self._device_name

    def out_of_fuel(self):
        return self._price > 1e5

    def status(self):
        return None

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=self._time,
            device_id = self._device_id
        )

    def calculate_next_ttie(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        found_event = None
        # search through the non-scheduled events first
        for event in self._events:
            if (event.ttie > self._time) and (found_event is None or (event.ttie < found_event.ttie)):
                found_event = event

        # check the scheduler for upcoming events
        if self._scheduler:
            sched_event = self._scheduler.get_next_scheduled_task(self._time)
            if sched_event and sched_event.ttie > self._time and (found_event is None or sched_event.ttie < found_event.ttie):
                # assign the vent with the lower ttie
                found_event = sched_event

        if not found_event is None and (self._ttie is None or self._ttie < found_event.ttie):
            # self._logger.debug(
                # self.build_message(message="the next event found is {}".format(found_event))
            # )
            self._events.append(found_event)
            self.broadcast_new_ttie(found_event.ttie)
            self._ttie = found_event.ttie

    def broadcast_new_price(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_price_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new price {} from {}".format(new_price, self._device_name),
                    tag="broadcast_price",
                    value=new_price
                )
            )
            self._broadcast_new_price_callback(self._device_id, target_device_id, self._time, new_price)
        else:
            raise Exception("broadcast_new_price has not been set for this device!")
        return

    def broadcast_new_power(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_power_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new power {} from {}".format(new_power, self._device_name),
                    tag="broadcast_power",
                    value=new_power
                )
            )
            self._broadcast_new_power_callback(self._device_id, target_device_id, self._time, new_power)
        else:
            raise Exception("broadcast_new_power has not been set for this device!")
        return

    def broadcast_new_capacity(self, value=None, target_device_id=None, debug_level=logging.DEBUG):
        "Broadcast the new capacity value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_capacity_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new capacity {} from {}".format(value, self._device_name),
                    tag="broadcast_capacity",
                    value=value if not value is None else self._current_capacity
                )
            )
            self._broadcast_new_capacity_callback(
                self._device_id,
                target_device_id if not target_device_id is None else self._grid_controller_id,
                self._time,
                self._current_capacity if value is None else value
            )
        else:
            raise Exception("broadcast_new_capacity has not been set for this device!")

    def broadcast_new_ttie(self, new_ttie, debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_ttie_callback):
            self._broadcast_new_ttie_callback(self._device_id, new_ttie)
        else:
            raise Exception("broadcast_new_ttie has not been set for this device!")
        return

    def time_of_day_seconds(self):
        "Get the time of day in seconds"
        return self._time % (24 * 60 * 60)

    def get_ttie(self):
        return self._ttie

    def turn_on(self):
        "Turn on the device"
        if not self._in_operation:
            self._logger.info(self.build_message(message="turn on device", tag="on/off", value=1))
            self._in_operation = True
            self.set_power_level()
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def turn_off(self):
        "Turn off the device"
        if self._in_operation:
            self._power_level = 0.0
            self._in_operation = False
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)
            self._logger.info(self.build_message(message="turn off device", tag="on/off", value=0))
            self._logger.info(
                self.build_message(
                    message="Power level {}".format(self._power_level),
                    tag="power",
                    value=self._power_level
                )
            )

    def is_on(self):
        return self._in_operation

    def should_be_in_operation(self):
        """determine if the device should be operating when a refresh event occurs"""
        return self._current_event and self._current_event.value == "on"

    def set_power_level(self):
        """Set the power output of the device"""
        self._power_level = self._max_power_output

    def refresh(self):
        "Refresh the eud. For a basic eud this means resetting the operation schedule."
        self._ttie = None
        self._events = []

        # turn on/off the device based on the updated schedule
        should_be_in_operation = self.should_be_in_operation()
        if should_be_in_operation and not self._in_operation:
            self.turn_on()
        elif not should_be_in_operation and self._in_operation:
            self.turn_off()

        self.calculate_next_ttie()

    def set_scenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

    def process_supervisor_event(self, the_event):
        if isinstance(the_event, LpdmTtieEvent):
            self._logger.debug("found lpdm ttie event {}".format(the_event))
            self.on_time_change(the_event.value)
        elif isinstance(the_event, LpdmPowerEvent):
            self._logger.debug("found lpdm power event {}".format(the_event))
            self.on_power_change(
                source_device_id=the_event.source_device_id,
                target_device_id=the_event.target_device_id,
                time=the_event.time,
                new_power=the_event.value
            )
        elif isinstance(the_event, LpdmPriceEvent):
            self._logger.debug("found lpdm price event {}".format(the_event))
            self.on_price_change(
                source_device_id=the_event.source_device_id,
                target_device_id=the_event.target_device_id,
                time=the_event.time,
                new_price=the_event.value
            )
        elif isinstance(the_event, LpdmCapacityEvent):
            self._logger.debug("found lpdm capacity event {}".format(the_event))
            self.on_capacity_change(
                source_device_id=the_event.source_device_id,
                target_device_id=the_event.target_device_id,
                time=the_event.time,
                value=the_event.value
            )
        elif isinstance(the_event, LpdmConnectDeviceEvent):
            self._logger.debug("found lpdm connect device event {}".format(the_event))
            self.add_device(the_event.device_id, the_event.DeviceClass)
        elif isinstance(the_event, LpdmAssignGridControllerEvent):
            self._logger.debug("found lpdm connect device event {}".format(the_event))
            self.assign_grid_controller(the_event.grid_controller_id)
        elif isinstance(the_event, LpdmKillEvent):
            self.finish()
            self._logger.debug("found a ldpm kill event {}".format(the_event))
        else:
            self._logger.error("event type not found {}".format(the_event))
        self._logger.debug("task finished")

