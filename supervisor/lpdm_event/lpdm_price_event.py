from lpdm_base_event import LpdmBaseEvent

class LpdmPriceEvent(LpdmBaseEvent):
    def __init__(self, source_device_id, target_device_id, value):
        LpdmBaseEvent.__init__(self, source_device_id, target_device_id, value)
        self.event_type = "price"
