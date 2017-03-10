import logging
from device_item import DeviceItem

class DeviceManager(object):
    def __init__(self):
        self.device_list = []
        self.logger = logging.getLogger("lpdm")

    def count(self):
        """Return the number of devices connected"""
        return len(self.device_list)

    def devices(self):
        """Generator function for iterating through devices"""
        for d in self.device_list:
            yield d

    def add(self, device_id, DeviceClass):
        """Register a device"""
        # make sure a device with the same id does not exist
        found = filter(lambda d: d.device_id == device_id, self.device_list)
        if len(found) == 0:
            self.device_list.append(DeviceItem(device_id, DeviceClass))
            self.logger.debug("message: registered a device {} - {}".format(device_id, DeviceClass))
        else:
            raise Exception("The device_id already exists {}".format(device_id))

    def set_load(self, device_id, load):
        """set the load for a device"""
        d = self.get(device_id)
        d.load = load

    def get(self, device_id):
        """Get the info for a device by its ID"""
        found = filter(lambda d: d.device_id == device_id, self.device_list)
        self.logger.debug("message: found device {}".format(found))
        if len(found) == 1:
            return found[0]
        else:
            raise Exception("An error occured trying to retrieve the device {}".format(device_id))
