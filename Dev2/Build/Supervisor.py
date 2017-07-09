"""

############MORE DOCUMENTATION HERE#################################

The supervisor class maintains a sorted map of the times of all initial events, mapping to the event with that time.

"""

from Build import Priority_queue


class Supervisor:

    def __init__(self):
        self._event_queue = Priority_queue.PriorityQueue()  # queue items are device_ids prioritized by next event time
        self._devices = {}

    """Given a pointer to a device, adds a mapping from device_id to that device"""
    def register_device(self, device):
        device_id = device.get_id()
        self._devices[device_id] = device

    def register_event(self, device_id, time_of_next_event):
        self._event_queue.add(device_id, time_of_next_event)

    def occur_next_event(self):
        device_id, time_of_next_event = self._event_queue.pop()
        if device_id in self._devices.keys():
            device = self._devices[device_id]
            device.advance_time(time_of_next_event)  # advance local time of device to its next event
            device.process_events()  # process all events at device's local time 0
            device_id, device_next_time = device.report_next_event_time()
            self.register_event(device_id, device_next_time)  # add the next earliest time for device
        else:
            raise KeyError("Device has not been properly initialized!")



