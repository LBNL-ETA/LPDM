from lpdm_base_event import LpdmBaseEvent

class LpdmTtieEvent(LpdmBaseEvent):
    def __init__(self, target_device_id, value):
        LpdmBaseEvent.__init__(self, source_device_id=None, target_device_id=target_device_id, value=value)
        self.event_type = "ttie"
