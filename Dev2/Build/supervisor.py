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
The supervisor's role is to

"""

from Build.priority_queue import PriorityQueue


class Supervisor:

    def __init__(self):
        self._event_queue = PriorityQueue()  # queue items are device_ids prioritized by next event time
        self._devices = {}  # dictionary of device_id's mapping to their associated devices. All devices in simulation.

    ##
    # Method to get the device pointer from a device_id, called by devices when they receive a message from a
    # device that they do not recognize.

    def get_device(self, device_id):
        if device_id in self._devices.keys():
            return self._devices[device_id]
        else:
            print('No such device')
            return None

    ##
    # Given a device, adds a mapping from device_id to that device
    # @param device the device to add to the supervisor device dictionary
    ##
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
        if device_id in self._devices.keys():
            device = self._devices[device_id]
            device.update_time(time_of_next_event)  # set the device's local time to the time of next event
            device.process_events()  # process all events at device's local time
            if device.has_upcoming_event():
                device_id, device_next_time = device.report_next_event_time()
                self.register_event(device_id, device_next_time)  # add the next earliest time for device
        else:
            raise KeyError("Device has not been properly initialized!")

    ##
    # Determines that the simulation should continue to run because there are unprocessed events in its queue
    def has_next_event(self):
        if self._event_queue.is_empty():
            print('yes')
        return not self._event_queue.is_empty()

