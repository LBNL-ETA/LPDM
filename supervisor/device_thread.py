import threading
import logging
import sys
import traceback
from lpdm_event import LpdmTtieEvent, LpdmPowerEvent, LpdmPriceEvent, LpdmInitEvent, LpdmKillEvent, \
    LpdmConnectDeviceEvent, LpdmAssignGridControllerEvent, LpdmRunTimeErrorEvent, \
    LpdmCapacityEvent

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

        # self.logger = logging.getLogger("lpdm")
        self.logger = logging.LoggerAdapter(logging.getLogger("lpdm"), {"sim_seconds": "", "device_id": "device_thread"})

    def run(self):
        self.logger.debug("run the device thread for device id {}".format(self.device_id))

        the_event = None
        # loop until a kill event is received
        while not isinstance(the_event, LpdmKillEvent):
            self.logger.debug("wait for the next event...")        
            the_event = self.queue.get()
            self.logger.debug('device has waken up')
            is_error = False

            try:
                if isinstance(the_event, LpdmInitEvent):
                    self.logger.debug("found an init event {}".format(the_event))
                    self.init_device()
                else:
                    if the_event:
                        self.device.process_event(the_event)
                self.logger.debug("task finished")
                self.queue.task_done()
            except Exception as e:
                is_error = True
                with open("/tmp/error", "a") as f:
                    f.write(str(the_event) + "\n")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
                self.logger.error("\n".join(tb))
                self.supervisor_queue.put(LpdmRunTimeErrorEvent("\n".join(tb)))
                self.queue.task_done()
                
            if not is_error:
                with open("/tmp/success", "a") as f:
                    f.write(str(the_event) + "\n")


    def init_device(self):
        """initialize the device"""
        self.add_callbacks_to_config(self.device_config)
        self.device = self.DeviceClass(self.device_config)
        self.device.init()

    def add_callbacks_to_config(self, config):
        """add the callback functions for power, price, ttie to the device configuration"""
        self.logger.debug("add the device callbacks for power, price, and ttie")
        config["broadcast_new_power"] = self.callback_new_power
        config["broadcast_new_price"] = self.callback_new_price
        config["broadcast_new_ttie"] = self.callback_new_ttie
        config["broadcast_new_capacity"] = self.callback_new_capacity

    def callback_new_power(self, source_device_id, target_device_id, time_value, value):
        """broadcast a power change"""
        self.logger.debug("message: power change event received")
        self.supervisor_queue.put(
            LpdmPowerEvent(source_device_id, target_device_id, time_value, value)
        )

    def callback_new_price(self, source_device_id, target_device_id, time_value, value):
        """broadcast  price change"""
        self.logger.debug("device: {}, message: Price change event received ({}, {}, {}, {})".format(
            self.device_id, source_device_id, target_device_id, time_value, value
        ))
        self.supervisor_queue.put(
            LpdmPriceEvent(source_device_id, target_device_id, time_value, value)
        )

    def callback_new_ttie(self, device_id, value):
        """register a new ttie for a device"""
        self.logger.debug("received new ttie {} - {}".format(device_id, value))
        self.supervisor_queue.put(LpdmTtieEvent(target_device_id=device_id, value=value))

    def callback_new_capacity(self, source_device_id, target_device_id, time_value, value):
        """register a new capacity for a device"""
        self.logger.debug("received new capacity {} - {}".format(source_device_id, value))
        self.supervisor_queue.put(
            LpdmCapacityEvent(source_device_id, target_device_id, time_value, value)
        )

