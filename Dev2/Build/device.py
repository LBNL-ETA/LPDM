"""

A device maintains a priority queue of functions prioritized by time.
The queue is a heap sorted by by time signature, with time in milliseconds from the current time for the event to be processed.
The


"""

from Build import Priority_queue
from Build import Event
from Build.Message import MessageType



class Device:

    def __init__(self, device_id, supervisor):
        self._device_id = device_id
        self._queue = Priority_queue.PriorityQueue()
        self._connected_devices = {}
        self._supervisor = supervisor

    ##
    # Adds an event to the device's event queue and reports that event to the supervisor
    # @param event the event to add to the event queue
    # @param time_stamp the time to associate with the event in the queue

    def add_event(self, event, time_stamp):
        self._queue.add(event, time_stamp)
        self._supervisor.register_event(self.report_next_event_time())

    ##
    # Getter for the Device's ID
    # We maintain ID as a protected field to avoid external modifications during messaging
    # @return the device's ID
    def get_id(self):
        return self._device_id

    ##
    # Advances time for the device by shifting all events in its queue down by a step value.
    # Note: Events will not be shifted down below zero.

    # @param step integer value to shift all event times by
    def advance_time(self, step):
        self._queue.shift(step)

    ##
    # Process all events in the device's queue with a time stamp of 0 (now).
    # This function should be called after advance_time has been called by the supervisor.

    def process_events(self):
        event, time_stamp = self._queue.pop()
        while time_stamp is 0:
            event.run_event()
            event, time_stamp = self._queue.pop()
        self._queue.add(event, time_stamp)  # add back the last removed item without time 0.

    ##
    # Report the time of the next earliest event in the device's event queue
    # @return a tuple of device's ID and the time of its next event

    def report_next_event_time(self):
        next_event, time_stamp = self._queue.peek()
        return self._device_id, time_stamp

    ##
    # Receiving a message is modelled as putting an event with the message 1 time step after the function call.
    #
    def receive_message(self, message):
        self.add_event(Event(self.read_message, message), message.time + 1)

    ##
    #
    # @param message a message to be read (must be a message object)
    def read_message(self, message):
        #  takes it apart into its components
        # TODO: log the sender read time
        if message.message_type == MessageType.REGISTER:
            # do stuff
            pass
        elif message.message_type == MessageType.POWER:
            #do stuff
            pass
        elif message.message_type == MessageType.PRICE:
            #do stuff
            pass
        else:
            raise NameError('Unverified Message Type')









