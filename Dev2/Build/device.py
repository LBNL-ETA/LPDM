"""

A device maintains a priority queue of functions prioritized by time.
The queue is a heap sorted by by time signature, with time in milliseconds from the current time for the event to be processed.
The


"""

from Build import Priority_queue
from Build import Event
from Build import Message
from abc import abstractmethod


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
    # Process all events in the device's queue with a given time_stamp.
    # This function should be called after advance_time has been called by the supervisor.

    def process_events(self, run_time):
        event, time_stamp = self._queue.pop()
        while time_stamp <= run_time:  # there shouldn't be any events less than run_time but just in case
            event.run_event()
            event, time_stamp = self._queue.pop()
        self._queue.add(event, time_stamp)  # add back the last removed item which wasn't processed.

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
        # TODO: log the sender and read time
        if message.message_type == Message.MessageType.REGISTER:
            self.register_device(message.sender, message.value)
        elif message.message_type == Message.MessageType.POWER:
            self.on_power_change(message.sender, message.value)
        elif message.message_type == Message.MessageType.PRICE:
            self.on_price_change(message.sender, message.value)
        elif message.message_type == Message.MessageType.ALLOCATE:
            self.on_allocate(message.sender, message.value)
        elif message.message_type == Message.MessageType.REQUEST:
            self.on_request(message.sender, message.value)
        else:
            raise NameError('Unverified Message Type')

    ##
    # Registers or unregisters a given device from the device's connected device list
    # @param device the device to register or unregister from connected devices
    # @param value positive to register, 0 or negative to unregister

    def register_device(self, device, value):
        # log this, BABY.
        device_id = device.get_id()
        if value > 0:
            self._connected_devices[device_id] = device
        else:
            if device_id in self._connected_devices:
                del self._connected_devices[device_id]  # unregister
            else:
                print("No Such Device To unregister")

    ##
    # Method to be called when the device receives a power message, indicating power flows
    # have changed between two devices (either receiving or providing).
    #
    # @param new_power the value of power flow, negative if receiving, positive if providing.
    @abstractmethod
    def on_power_message(self, sender, new_power):
        pass

    ##
    # Method to be called when device receives a price message
    #
    # @param new_price the new price value
    #  TODO: This occurs when a device sends a price message. Internal price modulation vs external? Different funcs?

    @abstractmethod
    def on_price_message(self, sender, new_price):
        pass

    ##
    # Method to be called when device receives a request message, indicating a device is requesting to
    # either provide or receive the requested quantity of power.
    #
    # @param request_amt the amount the device is requesting to provide (positive) or to receive (negative). s
    @abstractmethod
    def on_request(self, sender, request_amt):
        pass

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power. Allocation should only ever occur after request messages
    # have been passed and processed.
    #
    # @param allocated_amt the amount allocated to provide to another device (positive) or to receive from another
    # device (negative). s
    @abstractmethod
    def on_allocate(self, sender, allocate_amt):
        pass


    # TODO: (1) Implement EUD-GC Messaging (2) Port in EUD subclasses, (3) TEST! (4) Add PV, UtilityMeter Messaging
    # TODO: (5) Add Battery Functionality (6) MAJOR TESTING 


