class DeviceItem:
    def __init__(self, device_id, DeviceClass, load=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.load = 0.0

    def set_load(self, new_load):
        self.load = new_load
