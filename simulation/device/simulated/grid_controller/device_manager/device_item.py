class DeviceItem:
    def __init__(self, device_id, DeviceClass, uuid=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.uuid = uuid
        self.load = 0.0

    def set_load(self, new_load):
        self.load = new_load
