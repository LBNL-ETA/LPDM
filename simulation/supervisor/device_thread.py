import threading
import logging
import sys
import traceback
from lpdm_event import LpdmInitEvent, LpdmKillEvent, LpdmRunTimeErrorEvent, LpdmBaseEvent
from simulation_logger import message_formatter

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

        self.logger = logging.getLogger("lpdm")

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=None,
            device_id="device_thread"
        )

    def run(self):
        self.logger.debug(self.build_message("run the device thread for device id {}".format(self.device_id)))

        the_event = None
        # loop until a kill event is received
        while not isinstance(the_event, LpdmKillEvent):
            the_event = self.queue.get()

            try:
                if isinstance(the_event, LpdmInitEvent):
                    self.logger.debug(self.build_message("found an init event {}".format(the_event)))
                    self.init_device()
                else:
                    if the_event:
                        self.device.process_supervisor_event(the_event)
                self.queue.task_done()
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
                self.logger.error("\n".join(tb))
                self.supervisor_queue.put(LpdmRunTimeErrorEvent("\n".join(tb)))
                self.queue.task_done()

    def init_device(self):
        """initialize the device"""
        # add the supervisor callback to the config dictionary
        self.add_supervisor_callback(self.device_config)
        self.device = self.DeviceClass(self.device_config)
        self.device.init()
        self.device.set_initialized(True)

    def add_supervisor_callback(self, config):
        config["broadcast"] = self.supervisor_callback

    def supervisor_callback(self, broadcast_message):
        """Broadcast a message from a device to the supervisor/other devices"""
        # put the message in the supervisor's queue
        if not isinstance(broadcast_message, LpdmBaseEvent):
            raise Exception(
                "Attempt to pass a non BroadcastMessage object to the supervisor ({})".format(broadcast_message)
            )
        self.supervisor_queue.put(broadcast_message)
