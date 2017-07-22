"""


"""

from Build import Priority_queue


class Supervisor:

    def __init__(self):
        self._event_queue = Priority_queue.PriorityQueue()  # queue items are device_ids prioritized by next event time
        self._devices = {}

    ##
    # Given a pointer to a device, adds a mapping from device_id to that device
    # @param device the device to add to the supervisor device dictionary
    ##
    def register_device(self, device):
        device_id = device.get_id()
        self._devices[device_id] = device

    ##
    # Registers an event
    # @param device the device to add to the supervisor device dictionary
    ##

    def register_event(self, device_id, time_of_next_event):
        self._event_queue.add(device_id, time_of_next_event)

    ##
    # Runs the next event in the supervisor's queue, advancing that device's local time to that point

    def occur_next_event(self):
        device_id, time_of_next_event = self._event_queue.pop()
        if device_id in self._devices.keys():
            device = self._devices[device_id]
            device.process_events(time_of_next_event)  # process all events at device's local time
            device_id, device_next_time = device.report_next_event_time()
            self.register_event(device_id, device_next_time)  # add the next earliest time for device
        else:
            raise KeyError("Device has not been properly initialized!")

    ##
    # Determines that the simulation should continue to run because there are unprocessed events in its queue
    def has_next_event(self):
        return not self._event_queue.is_empty()

