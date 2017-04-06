from lpdm_base_event import LpdmBaseEvent

class LpdmRunTimeErrorEvent(LpdmBaseEvent):
    def __init__(self, description):
        LpdmBaseEvent.__init__(self)
        self.event_type = "run_time_error"
        self.description = description
