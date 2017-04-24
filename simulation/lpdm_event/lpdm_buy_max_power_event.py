from lpdm_base_event import LpdmBaseEvent

class LpdmBuyMaxPowerEvent(LpdmBaseEvent):
    """A power source notifies a grid controller the maximum amount of power it can buy at a time"""
    def __init__(self, source_device_id, target_device_id, time, value):
        LpdmBaseEvent.__init__(self, source_device_id, target_device_id, time, value)
        self.event_type = "buy_max_power"

