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
The supervisor's role is to maintain knowledge of all devices in the simulation and the soonest upcoming event for each.
The supervisor then 'creates time' by updating the time of each device in serial fashion when they have the next
earliest event, and then telling that device to process all of its events. The supervisor is also responsible for
calculating some of the final simulation power statistics.
"""

import logging

from Build.Simulation_Operation.queue import PriorityQueue
from Build.Objects.converter.converter import Converter
from Build.Objects.eud import Eud


class Supervisor:

    def __init__(self):
        self._event_queue = PriorityQueue()  # queue items are device_ids prioritized by next event time
        self._devices = {}  # dictionary of device_id's mapping to their associated devices. All devices in simulation.
        self._logger = logging.getLogger("lpdm")  # Setup logging

    ##
    # Method to get the device pointer from a device_id, called by devices when they receive a message from a
    # device that they do not recognize.

    def get_device(self, device_id):
        if device_id in self._devices:
            return self._devices[device_id]
        else:
            raise ValueError("There is no such requested device in the simulation " + device_id)

    ##
    # Returns the list of all devices in the simulation.
    #
    def all_devices(self):
        return self._devices.values()

    ##
    # Given a device, adds a mapping from device_id to that device
    # @param device the device to add to the supervisor device dictionary
    #

    def register_device(self, device):
        device_id = device.get_id()
        self._devices[device_id] = device

    ##
    # Registers an event
    # @param device_id the device to add to the supervisor device dictionary
    # @param time_of_next_event the time of the next event to add to event queue

    def register_event(self, device_id, time_of_next_event):
        self._event_queue.add(device_id, time_of_next_event)

    ##
    # Runs the next event in the supervisor's queue, advancing that device's local time to that point
    # Assumes queue is not empty. Call has_next_event first.

    def occur_next_event(self):
        device_id, time_of_next_event = self._event_queue.pop()
        if device_id in self._devices:
            device = self._devices[device_id]
            device.update_time(time_of_next_event)  # set the device's local time to the time of next event
            device.process_events()  # process all events at device's local time
            if device.has_upcoming_event():
                device_id, device_next_time = device.report_next_event_time()
                self.register_event(device_id, device_next_time)  # add the next earliest time for device
        else:
            raise KeyError("Device has not been properly initialized!")

    ##
    # Determines if the simulation is unfinished and there are unprocessed events in its queue

    def has_next_event(self):
        return not self._event_queue.is_empty()

    ##
    # Returns an (event, time_stamp) with next, or None.
    # Call has next event first to be safe.
    def peek_next_event(self):
        if self.has_next_event():
            return self._event_queue.peek()
        else:
            return None

    ##
    # Returns the total simulation power in and total simulation power out for the device.
    # Total simulation power in should approximately equal simulation power out, with small margin of error
    # allowed because of float rounding and because message latency slightly affects the calculations.

    def total_calcs(self):
        total_power_in = 0.0
        total_power_out = 0.0
        total_wire_loss_in = 0.0
        total_wire_loss_out = 0.0
        total_converter_loss_energy = 0.0
        total_eud_energy = 0.0
        for device in self._devices.values():
            total_power_in += device._sum_power_in
            total_power_out += device._sum_power_out
            total_wire_loss_in += device._wire_loss_in
            total_wire_loss_out += device._wire_loss_out
            if isinstance(device, Converter):
                total_converter_loss_energy += device._converter_loss_energy
            if isinstance(device, Eud):
                total_eud_energy += device._sum_power_in
        total_loss_energy = total_converter_loss_energy + total_wire_loss_in
        if total_eud_energy > 0:
            efficiency = 1 - total_loss_energy/total_eud_energy
        else:
            efficiency = 0
        self._logger.info("total simulation power in: {} Wh".format(total_power_in))
        self._logger.info("total simulation power out: {} Wh".format(total_power_out))
        self._logger.info("total simulation wire loss in: {} Wh".format(total_wire_loss_in))
        self._logger.info("total simulation wire loss out: {} Wh".format(total_wire_loss_out))
        self._logger.info("total simulation converter loss: {} Wh".format(total_converter_loss_energy))
        self._logger.info("total simulation loss: {} Wh".format(total_loss_energy))
        self._logger.info("total simulation EUD load: {} Wh".format(total_eud_energy))
        self._logger.info("total simulation efficiency: {} %".format(efficiency*100.0))

    ##
    # Called at the end of the simulation. Finishes each device and instructs them to write their energy
    # consumption calculations
    # @param end_time the time of the finish event, to update each device to so they can perform their calculations.
    def finish_all(self, end_time):
        for device in self._devices.values():
            device.finish(end_time)
        self.total_calcs()
