from lpdm_base_event import LpdmBaseEvent

class LpdmInitEvent(LpdmBaseEvent):
    def __init__(self):
        LpdmBaseEvent.__init__(self)
        self.event_type = "init"

