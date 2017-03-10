class PowerSourceItem:
    def __init__(self, device_id, DeviceClass, capacity=None, load=None, price=None):
        self.device_id = device_id
        self.DeviceClass = DeviceClass
        self.capacity = None
        self.load = 0.0
        self.price = None

