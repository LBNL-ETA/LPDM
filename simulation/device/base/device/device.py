

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
from ...scheduler import Scheduler, LpdmEvent
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
        self._price = config.get("price", 0.1)
        self._static_price = config.get("static_price", False)
        self._grid_controller_id = config.get("grid_controller_id", None)
        self._max_power_output = config.get("max_power_output", 0.0)
        self._is_real_device = config.get("is_real_device", False)

        # keep track of the total energy used
        self._sum_kwh = 0.0
        self._last_sum_kwh_update_time = 0

        # _schedule_array is the raw schedule passed in
        # _dail_y_schedule is the parsed schedule used by the device to schedule events
        self._scheduler = None
        self._schedule_array = config.get("schedule", None)
        # setup the price scheduler
        self._price_scheduler = None
        self._price_schedule_array = config.get("price_schedule", None)
        self._events = []
        self._current_event = None

        # hourly average price tracking
        # stores the last 24 average values
        self._hourly_prices = []
        # stores the price changes in the past hour
        self._hourly_price_list = []

        self._power_level = 0.0
        self._time = 0
        self._units = None
        self._in_operation = False
        self._ttie = None
        self._current_capacity = None

        self._is_initialized = False

        self._broadcast_callback = None
        if config.has_key("broadcast") and callable(config["broadcast"]):
            self._broadcast_callback = config["broadcast"]

        # Setup logging
        self._logger = logging.getLogger("lpdm")

        self._logger.info(
            self.build_message("initialized device #{} - {}".format(self._uuid, self._device_type))
        )

    def init(self):
        """Run any initialization functions for the device"""
        self.setup_schedule()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def set_initialized(self, initialized=True):
        self._is_initialized = initialized

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def setup_schedule(self):
        """Setup the on/off and price schedules"""
        self.setup_on_off_schedule()
        self.setup_price_schedule()

    def setup_on_off_schedule(self):
        """Setup the on/off schedule if one has been defined"""
        if type(self._schedule_array) is list:
            self._scheduler = Scheduler(self._schedule_array)
            self._scheduler.parse_schedule()

    def setup_price_schedule(self):
        """Setup the price schedule if one has been defined"""
        if type(self._price_schedule_array) is list:
            self._price_scheduler = Scheduler(self._price_schedule_array)
            self._price_scheduler.set_task_name("price")
            self._price_scheduler.parse_schedule()

    def set_hourly_price_calculation_event(self):
        "set the next event to calculate the avg hourly prices"
        new_event = LpdmEvent(self._time + 60 * 60.0, "hourly_price_calculation")
        # check if the event is already there
        found_items = filter(lambda d: d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)
            self._hourly_price_list = []

    def assign_grid_controller(self, grid_controller_id):
        """set the grid controller for the device"""
        self._logger.info(
            self.build_message("attach device to GC {}".format(grid_controller_id))
        )
        self._grid_controller_id = grid_controller_id

    def finish(self):
        "Gets called at the end of the simulation"
        self.set_power_level(0.0)
        self.write_calcs()

    def uuid(self):
        return self._uuid;

    def device_name(self):
        return self._device_name

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

    def schedule_next_events(self):
        self.set_hourly_price_calculation_event()
        if self._scheduler:
            self.set_next_scheduled_on_off_event()
        if self._price_scheduler:
            self.set_next_scheduled_price_event()

    def set_next_scheduled_on_off_event(self):
        """If there's a schedule, find the next on/off event"""
        # check if there's already one scheduled
        found = filter(lambda d: d.value in ['on', 'off'], self._events)
        if len(found) == 0:
            sched_event = self._scheduler.get_next_scheduled_task(self._time if self._is_initialized else self._time - 1)
            self._events.append(sched_event)
            self._logger.debug(self.build_message(message="set next on/off event {}".format(sched_event)))

    def set_next_scheduled_price_event(self):
        """If there's a schedule, find the next price event"""
        # check if there's already one scheduled
        found = filter(lambda d: d.name == "price", self._events)
        if len(found) == 0:
            sched_event = self._price_scheduler.get_next_scheduled_task(self._time if self._is_initialized else self._time - 1)
            self._events.append(sched_event)
            self._logger.debug(self.build_message(
                message="set next price event {}".format(sched_event),
                tag="next_price_event",
                value=sched_event.ttie))

    def set_price(self, new_price):
        """set the energy current price"""
        if self._price != new_price and not new_price is None:
            self._price = new_price
            self._hourly_price_list.append(new_price)
            # send a message to the grid controller if there is one assigned
            if not self._grid_controller_id is None:
                self.broadcast_new_price(self._price, self._grid_controller_id)

    def calculate_next_ttie(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        found_event = None
        # search through the non-scheduled events first
        for event in self._events:
            if (event.ttie > self._time or (found_event is None and not self._is_initialized)) and (found_event is None or (event.ttie < found_event.ttie)):
                found_event = event

        if not found_event is None and (self._ttie is None or self._ttie < found_event.ttie):
            self.broadcast_new_ttie(found_event.ttie)
            self._ttie = found_event.ttie

    def broadcast_new_price(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new price {} from {}".format(new_price, self._device_name),
                    tag="broadcast_price",
                    value=new_price
                )
            )
            self._broadcast_callback(LpdmPriceEvent(self._device_id, target_device_id, self._time, new_price))
        else:
            raise Exception("broadcast_new_price has not been set for this device!")
        return

    def broadcast_new_power(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new power {} from {}".format(new_power, self._device_name),
                    tag="broadcast_power",
                    value=new_power
                )
            )
            self._broadcast_callback(LpdmPowerEvent(self._device_id, target_device_id, self._time, new_power))
        else:
            raise Exception("broadcast_new_power has not been set for this device!")
        return

    def broadcast_new_capacity(self, value=None, target_device_id=None, debug_level=logging.DEBUG):
        "Broadcast the new capacity value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new capacity {} from {}".format(value, self._device_name),
                    tag="broadcast_capacity",
                    value=value if not value is None else self._current_capacity
                )
            )
            self._broadcast_callback(
                LpdmCapacityEvent(
                    self._device_id,
                    target_device_id if not target_device_id is None else self._grid_controller_id,
                    self._time,
                    self._current_capacity if value is None else value
                )
            )
        else:
            raise Exception("broadcast_new_capacity has not been set for this device!")

    def broadcast_new_ttie(self, new_ttie, debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_callback):
            self._broadcast_callback(LpdmTtieEvent(target_device_id=self._device_id, value=new_ttie))
        else:
            raise Exception("broadcast_new_ttie has not been set for this device!")
        return

    def time_of_day_seconds(self):
        "Get the time of day in seconds"
        return self._time % (24 * 60 * 60)

    def get_ttie(self):
        return self._ttie

    def turn_on(self, power_level=None):
        "Turn on the device"
        if not self._in_operation:
            self._logger.info(self.build_message(message="turn on device", tag="on/off", value=1))
            self._in_operation = True
            power_level = power_level if not power_level is None else self.calculate_power_level()
            self.set_power_level(power_level)
            self.broadcast_new_power(self._power_level, target_device_id=self._grid_controller_id)

    def turn_off(self):
        "Turn off the device"
        if self._in_operation:
            self.set_power_level(0.0)
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

    def calculate_power_level(self):
        """calculate how much power the device should be using, would be the max unless variable power output"""
        return self._max_power_output

    def set_power_level(self, new_power):
        """Set the power output of the device"""
        if self._power_level != new_power:
            # self._power_level = self._max_power_output
            self.sum_kwh()
            self._power_level = new_power
            self._logger.debug(self.build_message(
                message="set power level",
                tag="set_power_level",
                value=new_power
            ))

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

        self.schedule_next_events()
        self.calculate_next_ttie()

    def set_scenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

    def process_events(self):
        """Process any base class events"""
        remove_items = []
        for event in self._events:
            if self._time >= event.ttie and event.value == "hourly_price_calculation":
                self.calculate_hourly_price()
                remove_items.append(event)
        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

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
            self.add_device(the_event.device_id, the_event.DeviceClass, the_event.uuid)
        elif isinstance(the_event, LpdmAssignGridControllerEvent):
            self._logger.debug("found lpdm connect device event {}".format(the_event))
            self.assign_grid_controller(the_event.grid_controller_id)
        elif isinstance(the_event, LpdmKillEvent):
            self.finish()
            self._logger.debug("found a ldpm kill event {}".format(the_event))
        else:
            self._logger.info("event type not found {}".format(the_event))

    def sum_kwh(self):
        """Keep a running total of the energy used by the device"""
        time_diff = self._time - self._last_sum_kwh_update_time
        if time_diff > 0 and self._power_level:
            self._sum_kwh += self._power_level * (time_diff / 3600.0)
        self._last_sum_kwh_update_time = self._time

    def write_calcs(self):
        """Write any calculations to the database"""
        self._logger.info(self.build_message(
            message="sum kwh",
            tag="sum_kwh",
            value=self._sum_kwh / 1000.0
        ))

    def is_real_device(self):
        """Is the device real or simulated?"""
        return self._is_real_device

    def calculate_hourly_price(self):
        """This should be called every hour to calculate the previous hour's average fuel price"""
        hour_avg = None
        if len(self._hourly_price_list):
            hour_avg = sum(self._hourly_price_list) / float(len(self._hourly_price_list))
        elif self._price is not None:
            hour_avg = self._price
        self._logger.debug(self.build_message(
                message="hourly price",
                tag="hourly_price",
                value=hour_avg
            ))

        self._hourly_prices.append(hour_avg)
        if len(self._hourly_prices) > 24:
            # remove the oldest item if more than 24 hours worth of data
            self._hourly_prices.pop(0)
        self._hourly_price_list = []
