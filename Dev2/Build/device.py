"""

A device maintains a priority queue of functions prioritized by time.
The queue is a heap sorted by by time signature, with time in milliseconds from the current time for the event to be processed.
The


"""

from Build import Priority_queue
from Build import Event


class Device:

    def __init__(self, device_id, supervisor):
        self._device_id = device_id
        self._queue = Priority_queue.PriorityQueue()
        self._connected_devices = {}
        self._supervisor = supervisor

    def add_event(self, event, time_stamp):
        self._queue.add(event, time_stamp)
        self._supervisor.register_event(self.report_next_event_time())

    # Keep ID as a protected field
    def get_id(self):
        return self._device_id

    def advance_time(self, step):
        self._queue.shift(step)

    """Process all device events with time_stamp of 0 (now). This function is called after advance_time has been 
    called by the supervisor. """
    def process_events(self):
        event, time_stamp = self._queue.pop()
        while time_stamp is 0:
            event.run_event()
            event, time_stamp = self._queue.pop()
        self._queue.add(event, time_stamp)  # add back the last removed item without time 0.

    def report_next_event_time(self):
        next_event, time_stamp = self._queue.peek()
        return self._device_id, time_stamp

    def receive_message(self, message):
        self.add_event(Event(self.read_message, message), message.time + 1)

    def read_message(self, message):
        #  takes it apart into its components
        pass





