from lpdm_base_event import LpdmBaseEvent

class LpdmConnectDeviceEvent(LpdmBaseEvent):
    """Connect a device to a grid controller"""
    def __init__(self, device_id, device_type, DeviceClass=None):
        LpdmBaseEvent.__init__(self)
        self.event_type = "connect_device"
        self.device_id = device_id
        self.device_type = device_type
        self.DeviceClass = DeviceClass
