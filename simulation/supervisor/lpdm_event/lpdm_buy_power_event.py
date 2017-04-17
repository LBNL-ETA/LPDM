from lpdm_base_event import LpdmBaseEvent

class LpdmBuyPowerEvent(LpdmBaseEvent):
    """A grid controller notifies a power source how much power is available for purchase"""
    def __init__(self, source_device_id, target_device_id, time, value):
        LpdmBaseEvent.__init__(self, source_device_id, target_device_id, time, value)
        self.event_type = "buy_max_power"


