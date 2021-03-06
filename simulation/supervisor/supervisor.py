import sys
import traceback
import Queue
import threading
import logging
import pprint
from ttie_event_manager import TtieEventManager
from event_manager import EventManager
from lpdm_event import LpdmPowerEvent, LpdmPriceEvent, LpdmTtieEvent, LpdmCapacityEvent, LpdmRunTimeErrorEvent, \
        LpdmBuyMaxPowerEvent, LpdmBuyPowerPriceEvent, LpdmBuyPowerEvent
from device_thread_manager import DeviceThreadManager
from device_thread import DeviceThread
from common.device_class_loader import DeviceClassLoader
from simulation_logger import message_formatter

class Supervisor:
    """
    Responsible for managing threads and messages.
    The Supervisor creates a thread for each separate device.
    """
    def __init__(self):
        # this is the queue for receiving events from device threads
        self.queue = Queue.Queue()
        self.ttie_event_manager = TtieEventManager()
        self.device_thread_manager = DeviceThreadManager(supervisor_queue=self.queue)
        # get the app logger
        self.logger = logging.getLogger("lpdm")
        self.config = None
        self.max_ttie = None,
        self._device_id = "supervisor"
        self._time = 0

    def build_message(self, message="", tag="", value=""):
        """Build the log message string"""
        return message_formatter.build_message(
            message=message,
            tag=tag,
            value=value,
            time_seconds=self._time,
            device_id=self._device_id
        )

    def load_config(self, config):
        """ Load the configuration dict for the simulation. """
        self.config = config
        # calculate the max ttie (seconds)
        self.max_ttie = config.get('run_time_days', 7) * 24 * 60 * 60
        device_class_loader = DeviceClassLoader()
        device_sections = ["grid_controllers", "power_sources", "euds"]

        # build the devices: first grid_controllers, then generators, then euds
        for section in device_sections:
            for dc in config["devices"][section]:
                # is the simulated or real
                simulated_or_real = dc.get("simulated_or_real", "simulated")
                # get the device class from it's device_type
                DeviceClass = device_class_loader.get_device_class_from_name("device.{}.{}".format(simulated_or_real, dc["device_type"]))
                self.add_device(DeviceClass=DeviceClass, config=dc)

    def process_supervisor_events(self):
        """Process events in the supervisor's queue"""
        while not self.queue.empty():
            the_event = self.queue.get()
            if isinstance(the_event, LpdmTtieEvent):
                # new ttie event: add it to the ttie event list
                self.ttie_event_manager.add(the_event)
            elif isinstance(the_event, LpdmPowerEvent) \
                or isinstance(the_event, LpdmPriceEvent) \
                or isinstance(the_event, LpdmCapacityEvent) \
                or isinstance(the_event, LpdmBuyMaxPowerEvent) \
                or isinstance(the_event, LpdmBuyPowerEvent) \
                or isinstance(the_event, LpdmBuyPowerPriceEvent):
                # power or price event: call the thread and pass along the event
                # get the target thread and put the event in the queue
                # self.logger.debug(self.build_message("supervisor event {}".format(the_event)))
                t = self.device_thread_manager.get(the_event.target_device_id)
                t.queue.put(the_event)
                t.queue.join()
            elif isinstance(the_event, LpdmRunTimeErrorEvent):
                # an exception has occured, kill the simulation
                raise Exception("LpdmRunTimeErrorEvent encountered.")

    def add_device(self, DeviceClass, config):
        """
        Register a device with the supervisor.
        This will create the device in its own separate thread.
        Set the listen_for_power and listen_for_price variables to allow a device to receive global price and power
        notifications.
        """
        # create the new thread for the device
        self.device_thread_manager.add(DeviceClass, config)

    def dispatch_next_ttie(self):
        """Notify the device it's time to execute their next event"""
        # get the next ttie event
        next_ttie = self.ttie_event_manager.get()
        if next_ttie:
            if next_ttie.value < self.max_ttie:
                if next_ttie.value < self._time:
                    self.logger.error(
                        self.build_message("current time is {}, but trying to execute event {}".format(self._time, next_ttie))
                    )
                    raise Exception("TTIE events out of order.")
                self._time = next_ttie.value
                # self.logger.debug(self.build_message("ttie {}".format(next_ttie)))
                # get the device thread and put the event in the queue
                t = self.device_thread_manager.get(next_ttie.target_device_id)
                t.queue.put(next_ttie)
                t.queue.join()

                # process any other resulting events
                self.process_supervisor_events()
            else:
                self.logger.debug(
                    self.build_message("max ttie reached ({}), quit simulation".format(next_ttie.value))
                )
        else:
            self.logger.debug(
                self.build_message("No ttie found... quit.")
            )
        return next_ttie

    def wait_for_threads(self):
        """Wait for threads to finsih what their tasks"""
        self.device_thread_manager.wait_for_all()

    def run_simulation(self):
        """Start running the simulation"""
        self.logger.info(
            self.build_message("start the simulation")
        )
        try:
            # star tthe device threads
            self.device_thread_manager.start_all()
            # connect the devices
            self.device_thread_manager.connect_devices()
            # process any resulting events from the device.init()
            self.process_supervisor_events()
            # keep dispatching the next ttie events until finished
            while self.dispatch_next_ttie():
                pass
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
            self.logger.error(self.build_message("\n".join(tb)))
        finally:
            # kill all threads
            self.device_thread_manager.kill_all()

    def stop_simulation(self):
        """Clean up and destroy the simulation when finished"""
        self.device_thread_manager.kill_all()
