import logging
import Queue
from lpdm_event import LpdmInitEvent, LpdmKillEvent, LpdmConnectDeviceEvent, LpdmAssignGridControllerEvent
from device_thread import DeviceThread
from device.simulated.grid_controller import GridController
from device.base.power_source import PowerSource
from device.simulated.eud import Eud
from simulation_logger import message_formatter

class DeviceThreadManager(object):
    def __init__(self, supervisor_queue):
        self.logger = logging.getLogger("lpdm")
        self.supervisor_queue = supervisor_queue
        self.threads = []

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=None,
            device_id="device_thread_mgr"
        )

    def add(self, DeviceClass, device_config):
        """store a thread and linking device_id"""
        # check and make sure the device_id is not being used
        device_id = device_config.get("device_id")
        if self.get(device_id):
            # quit if get returns anytyhing other than None
            raise Exception("The device_id {} is being used by multiple devices".format(device_id))
        # create the message queue
        q = Queue.Queue(maxsize=1)
        # create the actual thread
        t = DeviceThread(
            name="Thread-{}".format(device_id),
            device_id=device_id,
            DeviceClass=DeviceClass,
            device_config=device_config,
            queue=q,
            supervisor_queue=self.supervisor_queue
        )
        # keep track of the thread along with its metadata
        self.threads.append(t)
        self.logger.debug(self.build_message("added device class {}".format(DeviceClass)))

    def get(self, device_id):
        """Get a "managed thread" by a device_id"""
        for t in self.threads:
            if t.device_id == device_id:
                return t
        return None

    def grid_controllers(self):
        """Return a list of grid controllers"""

    def start_all(self):
        """Start all of the threads"""
        self.logger.debug("Start all threads")
        # start all of the device threads
        # wait for each one to finish initializing
        for t in self.threads:
            self.logger.debug(self.build_message("starting thread {}".format(t.device_id)))
            t.queue.put(LpdmInitEvent())
            t.start()
            t.queue.join()
        self.logger.debug(self.build_message("finished starting threads"))

    def connect_devices(self):
        """
        Connect devices to the appropriate grid controllers,
        And let the eud's know which gc they're connected to
        """
        # find the grid controllers
        gcs = filter(lambda t: t.DeviceClass is GridController, self.threads)
        # find the power sources
        dgs = filter(lambda t: issubclass(t.DeviceClass, PowerSource), self.threads)
        # find the euds
        euds = filter(
            lambda t: not issubclass(t.DeviceClass, GridController) and not issubclass(t.DeviceClass, PowerSource), self.threads
        )

        # TODO: allow for more than 1 grid controller
        if len(gcs) > 1:
            raise Exception("Only 1 grid controller is allowed to run at a time.")

        gc = gcs[0]
        for dg in dgs:
            # put the event in the queue
            gc.queue.put(
                LpdmConnectDeviceEvent(
                    device_id=dg.device_config["device_id"],
                    device_type=dg.device_config["device_type"],
                    DeviceClass=dg.DeviceClass,
                    uuid=dg.device_config.get("uuid", None)
                )
            )
            # wait for the event to finish
            gc.queue.join()
            # let the device know which gc they're connected to
            dg.queue.put(
                LpdmAssignGridControllerEvent(grid_controller_id=gc.device_config["device_id"])
            )
            dg.queue.join()

        # add the eud's
        for eud in euds:
            # put the event in the queue
            gc.queue.put(
                LpdmConnectDeviceEvent(
                    device_id=eud.device_config["device_id"],
                    device_type=eud.device_config["device_type"],
                    DeviceClass=eud.DeviceClass,
                    uuid=eud.device_config.get("uuid", None)
                )
            )
            # wait for the event to finish
            gc.queue.join()

            # let the device know which gc they're connected to
            eud.queue.put(
                LpdmAssignGridControllerEvent(grid_controller_id=gc.device_config["device_id"])
            )
            eud.queue.join()

    def kill_all(self):
        """Gracefully kill all device threads"""
        self.logger.debug(self.build_message("kill all threads"))
        # send a kill event to each thread
        for t in self.threads:
            self.logger.debug(self.build_message('kill thread {}'.format(t.name)))
            t.queue.put(LpdmKillEvent())
            t.queue.join()

    def wait_for_all(self):
        """Wait for all threads (call join method for each thread)"""
        [t.join() for t in self.threads]
