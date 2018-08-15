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

A device is a semi-autonomous agent in the simulation, which utilizes messaging and power flows to interact
with other devices. A device will be a real world appliance with 'smart' functionality: it maintains in
computerized memory a history of its transactions, its connected devices, a local time, events which
it will have to process at a set time, and other state variables.

In its implementation, a device maintains a priority queue of functions prioritized by time,
which it then processes when instructed that time has passed by the
supervisor.

Devices also maintain common functionality of messaging and receiving messages.
Any type of device must be able to receive any type of message, but the sending
of messages can be limited to the specific type of device (not all device types can send
all message types).

Note on Device Identification (include in Documentation).

All GC's Device ID's must begin with 'GC'.
All EUD's Device ID's must begin with 'EUD'.
All Utility Meter's Device ID"s must begin with UM.
All PV Device ID's must begin with PV.

"""

import logging
from abc import ABCMeta, abstractmethod

from Build.Simulation_Operation.message import Message, MessageType

from Build.Simulation_Operation.support import format_time_from_seconds
from Build.Simulation_Operation.event import Event
from Build.Simulation_Operation.queue import PriorityQueue
from Build.Simulation_Operation.support import SECONDS_IN_DAY


class Device(metaclass=ABCMeta):

    ##
    # Initialize a device.
    #
    # @param device_id unique device ID. Must begin with type of device (see documentation).
    # @param device_type the type of this device (the most specific class descriptor)
    # @param uuid the device's emergency shutdown priority
    # @param time device's local time, in seconds. This will be updated by the supervisor.
    # @param msg_latency the delay time before this device processes a received message.
    # @param connected_devices a list of the names of connected devices for this device.

    def __init__(self, device_id, device_type, supervisor, time=0, msg_latency=0, schedule=None, multiday=0,
                 total_runtime=SECONDS_IN_DAY, connected_devices=None):

        # TODO: Make it so that connected devices maps from device id to Wire, Device tuple.

        if connected_devices is None:
            self._connected_devices = {}
        else:
            self._connected_devices = {device.get_id(): device for device in connected_devices}

        self._device_id = device_id
        self._device_type = device_type
        self._queue = PriorityQueue()
        self._supervisor = supervisor
        self._time = time
        self._msg_latency = msg_latency
        self._time_last_power_in_change = time  # records the last time power levels into device changed
        self._time_last_power_out_change = time  # records the last time power levels out of device changed
        self._power_in = 0.0  # the power being consumed by the device (Watts, must be > 0)
        self._power_out = 0.0  # the power being distributed by the device (Watts, must be > 0)
        self._sum_power_out = 0.0  # Record the total energy produced by this device (wH)
        self._sum_power_in = 0.0  # Record the total energy produced by this device (wH)

        self._wire_loss_in = 0.0
        self._time_last_wire_loss_in = time
        self._wire_loss_out = 0.0
        self._time_last_wire_loss_out = time
        # keeps track of the wire loss for each device
        self._wire_loss_info_in = {}
        self._wire_loss_info_out = {}
        # dictionary of wires connected to this device, where the keys are device id's
        self._wires = {}
        # indicates if there's a wire connected to this device
        self._is_wired = False

        if schedule:
            self.setup_schedule(schedule, multiday=multiday, runtime=total_runtime)

        self._logger = logging.getLogger("lpdm")  # Setup logging
        self._logger.info(
            self.build_log_notation("initialize {} - {}".format(self._device_id, self._device_type))
        )
    
    def init(self):
        pass

    # ____________________________ Maintenance Functions _________________________________#

    ##
    # Getter for the Device's ID
    # We maintain ID as a protected field to avoid external modifications during messaging
    # @return the device's ID
    def get_id(self):
        return self._device_id

    ##
    # Getter for the Device's type
    def get_type(self):
        return self._device_type

    ##
    # Updates the local time of the device.
    # This method is only called by the Supervisor once it is about to process a next initial event.
    # @param new_time the time to update to
    def update_time(self, new_time):
        self._time = new_time

    ##
    # Sets the power level into the device. Call this method when setting absolute power levels
    # e.g. turning the device off
    #
    # @param power_in the new amount of power in to device (non-negative).

    def set_power_in(self, power_in):
        if power_in >= 0:
            self.sum_power_in()  # record all power usage at the previous power level.
            self._power_in = power_in
        else:
            raise ValueError("Power Level In Must Be Non-Negative")

    ##
    # Sets the power level out of the device. Call this method when setting absolute power levels
    # e.g. turning the device off
    #
    # @param power_in the new amount of power in to device (non-negative).

    def set_power_out(self, power_out):
        if power_out >= 0:
            self.sum_power_out()  # record all previous power usage at the previous level.
            self._power_out = power_out
        else:
            raise ValueError("Power Level Out Must Be Non-Negative")
    
    def calculate_wire_loss(self, device_id, amount):
        """Calculate the wire loss given a device_id

        Parameters
        ----------
        device_id: str
            The device_id of the device whose wire we need information
        amount: float
            Amount of power flowing through wire

        Returns
        -------
        float:
            The wire loss rate of the wire connected to device_id
        """
        # if wire:
        #     print(str(amount) + " " + str(wire))
        # else:
        #     print(str(self._device_id) + "  " +str(device_id) + "  " + str(self._wires.keys()))
        if amount < 0:
            # only calculates wire loss for positive amount
            return 0
        wire = self._wires.get(device_id, None)
        if wire:
            wire_loss = wire.calculate_power(amount)
            return wire_loss
            # return -wire_loss if amount and amount < 0 else wire_loss
        else:
            return 0

    def update_wire_loss_in(self, device_id, wire_loss_rate):
        "Update the wire loss rate for power flowing into the device"
        previous = self._wire_loss_info_in.get(device_id, 0)
        if previous and wire_loss_rate:
            self.sum_wire_loss_in(previous)
        self._wire_loss_info_in[device_id] = wire_loss_rate

    def update_wire_loss_out(self, device_id, wire_loss_rate):
        "Update the wire loss rate for power flowing into the device"
        previous = self._wire_loss_info_out.get(device_id, 0)
        if previous and wire_loss_rate:
            self.sum_wire_loss_in(previous)
        self._wire_loss_info_out[device_id] = wire_loss_rate

        
    ##
    # After a device has changed the quantity of power it is sending/receiving, modify the power in and power out.
    # Call whenever a load has been changed on this device.
    # @param prev_power the previous power flow from this device's perspective (in positive, out negative)
    # @param new_power the new power flow from this device's perspective (in positive, out negative)
    def recalc_sum_power(self, prev_power, new_power):
        # log power usage at previous power level.
        self.sum_power_in()
        self.sum_power_out()
        if prev_power >= 0:
            if new_power >= 0:
                self._power_in += (new_power - prev_power)
            elif new_power < 0:
                self._power_in -= prev_power
                self._power_out -= new_power
        elif prev_power < 0:
            if new_power >= 0:
                self._power_in += new_power
                self._power_out += prev_power
            elif new_power < 0:
                self._power_out -= (new_power - prev_power)
        return 0

    ##
    # Keeps a running total of the energy output by the device
    # Call this method whenever power_out level changes.

    def sum_power_out(self):
        time_diff = self._time - self._time_last_power_out_change
        if time_diff > 0:
            self._sum_power_out += self._power_out * (time_diff / 3600.0)  # Return in wH
        self._time_last_power_out_change = self._time

    ##
    # Keeps a running total of the energy consumed by the device
    # Call this method whenever power_in level changes.

    def sum_power_in(self):
        time_diff = self._time - self._time_last_power_in_change
        if time_diff > 0:
            self._sum_power_in += self._power_in * (time_diff / 3600.0)  # Return in wH
            self._logger.info(
                self.build_log_notation(
                    message="energy_in, dt = {}, load = {}".format(time_diff / 3600.0, self._power_in),
                    tag="energy_in",
                    value=self._power_in * (time_diff / 3600.0)
                )
            )
        self._time_last_power_in_change = self._time

    def sum_wire_loss_in(self, wire_loss_rate):
        time_diff = self._time - self._time_last_wire_loss_in
        if time_diff > 0:
            # Wh = W*s*(h/3600s)
            wire_loss_energy = wire_loss_rate * (time_diff / 3600.0)
            #wire_loss_energy = wire_loss_rate * time_diff * (time_diff / 3600.0)
            self._wire_loss_in += wire_loss_energy
            self._logger.info(
                self.build_log_notation(
                    message="Calculate wire-loss-in, dt = {}, rate = {}, energy = {}".format(time_diff / 3600.0, wire_loss_rate, wire_loss_energy),
                    tag="wire_loss_in",
                    value=wire_loss_energy
            ))
        self._time_last_wire_loss_in = self._time
    
    def sum_wire_loss_out(self, wire_loss_rate):
        time_diff = self._time - self._time_last_wire_loss_out
        if time_diff > 0:
            wire_loss_energy = wire_loss_rate * (time_diff / 3600.0)
            #wire_loss_energy = wire_loss_rate * time_diff * (time_diff / 3600.0)
            self._wire_loss_out += wire_loss_energy
            self._logger.info(
                self.build_log_notation(
                    message="Calculate wire-loss-out, dt = {}, rate = {}, energy = {}".format(time_diff / 3600.0, wire_loss_rate, wire_loss_energy),
                    tag="wire_loss_out",
                    value=wire_loss_energy
            ))
        self._time_last_wire_loss_out = self._time

    #  ______________________________________Internal State Functions _________________________________#

    ##
    # Adds an event to the device's event queue and reports that event to the supervisor
    # Will replace any existing event with the new value. Hence, only one event type at a time
    # @param event the event to add to the event queue
    # @param time_stamp the time to associate with the event in the queue

    def add_event(self, event, time_stamp):
        self._queue.add(event, time_stamp)
        device_id, next_time = self.report_next_event_time()
        self._supervisor.register_event(device_id, next_time)

    ##
    # Process all events in the device's queue with a given time_stamp.
    # This function should be called after advance_time has been called by the supervisor.
    def process_events(self):
        if self.has_upcoming_event():
            event, time_stamp = self._queue.peek()
            if time_stamp < self._time:
                raise ValueError("Time was incremented while there was an unprocessed event.")
            while time_stamp == self._time and self.has_upcoming_event():
                # process current events. Skylar was here.
                self._queue.pop()
                event.run_event()
                if self.has_upcoming_event():
                    event, time_stamp = self._queue.peek()

    def has_upcoming_event(self):
        return not self._queue.is_empty()

    ##
    # Report the time of the next earliest event in the device's event queue
    # Assumes the event queue is not empty. Call has_upcoming_event first.
    # @return a tuple of device's ID and the time of its next event

    def report_next_event_time(self):
        if not self.has_upcoming_event():
            raise ValueError("No upcoming events for this device")
        next_event, time_stamp = self._queue.peek()
        return self._device_id, time_stamp

    #  ______________________________________ Messaging/Interactive Functions_________________________________#

    ##
    # Receiving a message is modelled as putting an event with the message a certain delay after the function call.
    # @param message the message to receive.
    def receive_message(self, message):
        self.add_event(Event(self.read_message, message), message.time + self._msg_latency)

    ##
    # Reads a message and responds based on its message type
    # @param message a message to be read (must be a message object)
    def read_message(self, message):
        if message:
            self._logger.info(self.build_log_notation(
                "Read {} from {} with value {}".format(message.message_type, message.sender_id, message.value)))
            if message.message_type == MessageType.REGISTER:
                self.process_register_message(message)
            elif message.sender_id in self._connected_devices:  # Only read other messages from verified devices.
                if message.message_type == MessageType.POWER:
                    self.process_power_message(message)
                elif message.message_type == MessageType.PRICE:
                    self.process_price_message(message)
                elif message.message_type == MessageType.ALLOCATE:
                    self.process_allocate_message(message)
                elif message.message_type == MessageType.REQUEST:
                    self.process_request_message(message)
                else:
                    raise NameError('Unverified Message Type')

    ##
    # Registers or unregisters a given device from the device's connected device list
    # @param device the device to register or unregister from connected devices
    # @param that device's id
    # @param value positive to register, 0 or negative to unregister
    # TODO: Make this so it also registers that device across a wire (add wire param)

    def register_device(self, device, device_id, value, wire=None):
        if value > 0 and device_id not in self._connected_devices:
            self._connected_devices[device_id] = device
            if not device_id in self._wires:
                self._wires[device_id] = wire
                if not wire is None:
                    self._is_wired = True
            self._logger.info(
                self.build_log_notation("registered {}".format(device_id))
            )
        elif value > 0 and device_id in self._connected_devices and not wire is None:
            self._wires[device_id] = wire
            self._is_wired = True
            self._logger.info(
                self.build_log_notation("added wire to {}".format(device_id))
            )            
        # else:
        #     raise Exception("Device {} already registered to {}".format(device_id, self._device_id))
            # if device_id in self._connected_devices:
            #     del self._connected_devices[device_id]  # unregister
            #     if device_id in self._wires:
            #         del self._wires[device_id]
            #     self._logger.info(
            #         self.build_log_notation("unregistered {}".format(device_id))
            #     )
            # else:
            #     print("No Such Device To Unregister")

    ##
    # Method to be called when the device receives a register message, indicating a device
    # is seeking to register or unregister
    #
    # @param sender the sender of the message informing of registering.
    # @param value positive if sender is registering negative if unregistering

    # TODO: Make this so this message type includes wire in the extra information
    def process_register_message(self, message):
        if message.sender_id in self._connected_devices:
            sender = self._connected_devices[message.sender_id]
        else:
            sender = self._supervisor.get_device(message.sender_id)  # not in local table. Ask supervisor for the pointer to it.
        self.register_device(sender, message.sender_id, message.value)

    ##
    # Method to be called when the device wants to register or unregister with another device
    # @param target_id the device to receive the register message
    # @param value positive if registering negative if unregistering

    def send_register_message(self, target_id, value):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This device is not connected to the message recipient")
            # LOG THIS ERROR AND ALL ERRORS.
        self._logger.debug(self.build_log_notation(
            "REGISTER to {}".format(target_id), tag="register msg", value=value))
        target.receive_message(Message(self._time, self._device_id, MessageType.REGISTER, value))

    ##
    # Method to be called when device is entering the grid, and is seeking to register with other devices.
    #
    # @param device_list the connected list of devices to add to its connected device list and to inform it has
    # registered. Must be devices themselves (not ID's).

    def engage(self, device_list):
        for device in device_list:
            device_id = device.get_id()
            if device_id not in self._connected_devices:
                self._connected_devices[device_id] = device
            self.send_register_message(device_id, 1)

    ##
    # Method to be called when the device receives a power message, indicating power flows
    # have changed between two devices (either receiving or providing).
    #
    # @param sender the sender of the message providing or receiving the new power
    # @param new_power the value of power flow from sender's perspective
    # positive if sender is receiving, negative if sender is providing.

    @abstractmethod
    def process_power_message(self, message):
        pass

    ##
    # Method to be called when device receives a price message
    #
    # @param sender_id the sender of the message informing of the new price
    # @param new_price the new price value
    # @param extra_info additional information contained in this price message. From the utility meter,
    # this is its buy prices, from other devices this can be price forecast information.
    @abstractmethod
    def process_price_message(self, message):
        pass

    ##
    # Method to be called when device receives a request message, indicating a device is requesting to
    # either provide or receive the requested quantity of power.
    #
    # @param request_amt the amount the sending device is requesting to receive (must be positive)
    @abstractmethod
    def process_request_message(self, message):
        pass

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power. Allocation should only ever occur after request messages
    # have been passed and processed.
    #
    # @param allocated_amt the amount this device has been allocated to receive (must be positive).
    @abstractmethod
    def process_allocate_message(self, message):
        pass

    @abstractmethod
    def last_wire_loss_calc(self):
        pass

    # ______________________________SCHEDULING FUNCTIONALITY___________________________ #

    ##
    #
    # @param a list of scheduled events to add to the device's queue, in the format of list of list of
    # time(seconds), operation_name
    #
    def setup_schedule(self, scheduled_events, runtime=SECONDS_IN_DAY, multiday=0):
        curr_day = 0
        if multiday:
            while curr_day < runtime:
                for task in scheduled_events:
                    hour, operation_name, *args = tuple(task)
                    if hour > multiday * 24:
                        break  # Past our repeat interval
                    if hasattr(self, operation_name):
                        func = getattr(self, operation_name)
                    else:
                        raise ValueError("Called the scheduler with an incorrectly named function")
                    event = Event(func, *args) if args else Event(func)
                    time_sec = hour * 3600
                    self.add_event(event, curr_day + time_sec)
                curr_day += SECONDS_IN_DAY
        else:
            for task in scheduled_events:
                hour, operation_name, *args = tuple(task)
                if hasattr(self, operation_name):
                    func = getattr(self, operation_name)
                else:
                    raise ValueError("Called the scheduler with an incorrectly named function")
                event = Event(func, *args) if args else Event(func)
                time_sec = hour * 3600
                self.add_event(event, time_sec)

    # _____________________________ LOGGING FUNCTIONALITY ____________________________ #

    ##
    # Builds a logging message from a message, tag, and value, which also includes time and device_id
    # @param message the message to add to logger
    # @param tag the tag to associate with this message to add to the logger
    # @param value the value for this message to add to the logger

    # @return a formatted string to include in the logger
    def build_log_notation(self, message="", tag="", value=None):
        return "{}; {}; {}; {}; {}; {}".format(
            format_time_from_seconds(self._time), self._time, self._device_id, tag, value, message)

    ##
    # Writes the calculations of total energy in and out of this device in wH to the log file
    # then writes any other calculations specific to the device-type.

    def write_calcs(self):
        self._logger.info(self.build_log_notation(
            message="sum Wh out".format(self._device_id),
            tag="power calcs",
            value=self._sum_power_out
        ))
        self._logger.info(self.build_log_notation(
            message="sum Wh in",
            tag="power calcs",
            value=self._sum_power_in
        ))
        self._logger.info(self.build_log_notation(
            message="sum wire loss (Wh) in",
            tag="wire loss in",
            value=self._wire_loss_in
        ))
        self._logger.info(self.build_log_notation(
            message="sum wire loss (Wh) out",
            tag="wire loss out",
            value=self._wire_loss_out
        ))
        self.device_specific_calcs()

    ##
    # All device specific power consumption/runtime statistics are added here
    @abstractmethod
    def device_specific_calcs(self):
        pass

    ##
    # Method to be called at end of simulation resetting power levels and calculating
    # end_time the time to update the local time to
    def finish(self, end_time):
        """"Gets called at the end of the simulation"""
        self._time = end_time
        self.set_power_in(0.0)
        self.set_power_out(0.0)
        self.last_wire_loss_calc()
        self.write_calcs()

# _____________________________________________________________________ #

# INFRASTRUCTURE NECESSARY FOR TESTING ALGORITHMS.

# TODO: Implement the new Wire class, etc.
# TODO: Change Grid Controller's input file "threshold_alloc" to "minimum allocate response".
# TODO: Linear interpolation in Air Conditioner?
# TODO: Loads->Powerflows
# TODO: Load profile EUD.
