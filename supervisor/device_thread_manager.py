import logging
import Queue
from lpdm_event import LpdmInitEvent, LpdmKillEvent
from device_thread import DeviceThread

class DeviceThreadManager(object):
    def __init__(self, supervisor_queue):
        self.supervisor_queue = supervisor_queue
        self.threads = []

    def add(self, device_id, DeviceClass, device_config):
        """store a thread and linking device_id"""
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

    def get(self, device_id):
        """Get a "managed thread" by a device_id"""
        for t in self.threads:
            if t.device_id == device_id:
                return t
        return None

    def start_all(self):
        """Start all of the threads"""
        logging.info("Start all threads")
        # start all of the device threads
        # [t.thread.start() for t in self.threads]
        for t in self.threads:
            logging.debug("starting thread {}".format(t.device_id))
            t.queue.put(LpdmInitEvent())
            t.start()
            t.queue.join()
        logging.info("finished starting threads")

    def kill_all(self):
        """Gracefully kill all device threads"""
        logging.debug("kill all threads")
        # send a kill event to each thread
        for t in self.threads:
            logging.debug('kill thread {}'.format(t.name))
            t.queue.put(LpdmKillEvent())
            t.queue.join()
        logging.debug("finished killing threads")

    def wait_for_all(self):
        """Wait for all threads (call join method for each thread)"""
        logging.info("wait for all threads")
        [t.join() for t in self.threads]
        logging.info("finished waiting for threads")
