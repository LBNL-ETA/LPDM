

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

        self._power_level = 0.0
        self._time = 0
        self._units = None
        self._in_operation = False
        self._ttie = None
        self._next_event = None

        self._broadcast_new_price_callback = config["broadcast_new_price"] if type(config) is dict and  "broadcast_new_price" in config.keys() and callable(config["broadcast_new_price"]) else None
        self._broadcast_new_power_callback = config["broadcast_new_power"] if type(config) is dict and "broadcast_new_power" in config.keys() and callable(config["broadcast_new_power"]) else None
        self._broadcast_new_ttie_callback = config["broadcast_new_ttie"] if type(config) is dict and "broadcast_new_ttie" in config.keys() and callable(config["broadcast_new_ttie"]) else None
        self._broadcast_new_capacity_callback = config["broadcast_new_capacity"] if type(config) is dict and "broadcast_new_capacity" in config.keys() and callable(config["broadcast_new_capacity"]) else None

        # Setup logging
        self._logger = logging.getLogger("lpdm")

        self.log_message("initialized device #{} - {}".format(self._uuid, self._device_type))

    def init(self):
        """Run any initialization functions for the device"""
        self.calculate_next_ttie()

    def __repr__(self):
        "Default string representation of an object, prints out all attributes and values"
        return ", ".join(["{0} = {1}".format(key, getattr(self,key)) for key in self.__dict__.keys() if not callable(getattr(self, key))])

    def assign_grid_controller(self, grid_controller_id):
        """set the grid controller for the device"""
        self.log_message("attach device to GC {}".format(grid_controller_id))
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

    def log_message(self, message='', log_level=logging.DEBUG, tag=None, value=None):
        "Logs a message using the loggin module, default debug level is set to INFO"
        message = self.get_log_message_string(message, tag, value)
        self._logger.log(log_level, message)

    def get_log_message_string(self, message, tag=None, value=None):
        time_string = "Day {0} {1} ({2})".format(
                1 + int(self._time / (60 * 60 * 24)),
                datetime.datetime.utcfromtimestamp(self._time).strftime('%H:%M:%S'), self._time
        )
        return "time_string: {}, time_value: {}, device: {}, message: {}, tag: {}, value: {}".format(
                time_string, self._time, self._device_id, message, tag, value)

    def calculate_next_ttie(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        the_event = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]
                the_event = event

        if ttie != None and ttie != self._ttie:
            self.log_message("the next event found is {} at time {}".format(the_event, ttie))
            self.broadcast_new_ttie(ttie)
            self._ttie = ttie

    def broadcast_new_price(self, new_price, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast a new price if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_price_callback):
            self.log_message(
                message="Broadcast new price {} from {}".format(new_price, self._device_name),
                tag="broadcast_price",
                value=new_price
            )
            self._broadcast_new_price_callback(self._device_id, target_device_id, self._time, new_price)
        else:
            raise Exception("broadcast_new_price has not been set for this device!")
        return

    def broadcast_new_power(self, new_power, target_device_id='all', debug_level=logging.DEBUG):
        "Broadcast the new power value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_power_callback):
            self.log_message(
                message="Broadcast new power {} from {}".format(new_power, self._device_name),
                tag="broadcast_power",
                value=new_power
            )
            self._broadcast_new_power_callback(self._device_id, target_device_id, self._time, new_power)
        else:
            raise Exception("broadcast_new_power has not been set for this device!")
        return

    def broadcast_new_ttie(self, new_ttie, debug_level=logging.DEBUG):
        "Broadcast the new TTIE if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_ttie_callback):
            self._broadcast_new_ttie_callback(self._device_id, new_ttie)
        else:
            raise Exception("broadcast_new_ttie has not been set for this device!")
        return

    def broadcast_new_capacity(self, value=None, target_device_id=None, debug_level=logging.DEBUG):
        "Broadcast the new capacity value if a callback has been setup, otherwise raise an exception."
        if callable(self._broadcast_new_capacity_callback):
            self.log_message(
                message="Broadcast new capacity {} from {}".format(value, self._device_name),
                tag="broadcast_capacity",
                value=value
            )
            self._broadcast_new_capacity_callback(
                self._device_id,
                target_device_id if not target_device_id is None else self._grid_controller_id,
                self._time,
                value if not value is None  else self._capacity
            )
        else:
            raise Exception("broadcast_new_capacity has not been set for this device!")
        return

    def time_of_day_seconds(self):
        "Get the time of day in seconds"
        return self._time % (24 * 60 * 60)

    def get_ttie(self):
        return self._ttie

    def turn_on(self):
        "Turn on the device"
        self.log_message("{} turned on".format(self._device_name), tag="on/off", value=1)
        self._in_operation = True

    def turn_off(self):
        "Turn off the device"
        self.log_message("{} turned off".format(self._device_name), tag="on/off", value=0)
        self._in_operation = False

    def is_on(self):
        return self._in_operation

    def refresh(self):
        "Override to define operation for a device when a parameter has been reset and the device needs to be refreshed"
        return None

    def set_scenario(self, scenario):
        "Sets a 'scenario' for the device. Given a scenario in JSON format, sets various parameters to specific values"
        for key in scenario.keys():
            setattr(self, "_" + key, scenario[key])

