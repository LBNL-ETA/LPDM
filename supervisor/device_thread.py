import threading
import logging
from lpdm_event import LpdmTtieEvent, LpdmPowerEvent, LpdmPriceEvent, LpdmInitEvent, LpdmKillEvent

class DeviceThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None,
            device_id=None, DeviceClass=None, device_config=None, queue=None, supervisor_queue=None):
        threading.Thread.__init__(self, group=group, target=target, name=name, verbose=verbose)
        self.args = args
        self.kwargs = kwargs

        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.device_config = device_config
        self.queue = queue
        self.supervisor_queue = supervisor_queue
        self.device = None

    def run(self):
        logging.info("run the device thread for device id {}".format(self.device_id))

        the_event = None
        # loop until a kill event is received
        while not isinstance(the_event, LpdmKillEvent):
            logging.debug("wait for the next event...")
            the_event = self.queue.get()
            logging.debug('device has waken up')

            if isinstance(the_event, LpdmInitEvent):
                logging.debug("found an init event {}".format(the_event))
                self.init_device()
            elif isinstance(the_event, LpdmTtieEvent):
                logging.debug("found lpdm event {}".format(the_event))
                self.device.time_changed(the_event.value)
            elif isinstance(the_event, LpdmPowerEvent):
                logging.debug("found lpdm power event {}".format(the_event))
                self.device.power_changed(the_event.value)
            elif isinstance(the_event, LpdmKillEvent):
                logging.debug("found a ldpm kill event {}".format(the_event))
            else:
                logging.error("event type not found {}".format(the_event))
            logging.debug("task finished")
            self.queue.task_done()

    def init_device(self):
        """initialize the device"""
        self.add_callbacks_to_config(self.device_config)
        self.device = self.DeviceClass(self.device_config)

    def add_callbacks_to_config(self, config):
        """add the callback functions for power, price, ttie to the device configuration"""
        logging.debug("add the device callbacks for power, price, and ttie")
        config["broadcastNewPower"] = self.callback_new_power
        config["broadcastNewPrice"] = self.callback_new_price
        config["broadcastNewTtie"] = self.callback_new_ttie

    def callback_new_power(self, source_device_id, target_device_id, time_value, value):
        """broadcast a power change"""
        logging.debug("power change event received")
        self.supervisor_queue.put(LpdmPowerEvent(source_device_id, target_device_id, value))

    def callback_new_price(self, source_device_id, target_device_id, time_value, value):
        """broadcast  price change"""
        logging.debug("Price change event received")
        self.supervisor_queue.put(LpdmPriceEvent(source_device_id, target_device_id, value))

    def callback_new_ttie(self, device_id, value):
        """register a new ttie for a device"""
        logging.debug("received new ttie {} - {}".format(device_id, value))
        self.supervisor_queue.put(LpdmTtieEvent(target_device_id=device_id, value=value))
