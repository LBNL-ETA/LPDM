from lpdm_base_event import LpdmBaseEvent

class LpdmKillEvent(LpdmBaseEvent):
    def __init__(self):
        LpdmBaseEvent.__init__(self)
        self.event_type = "kill"

