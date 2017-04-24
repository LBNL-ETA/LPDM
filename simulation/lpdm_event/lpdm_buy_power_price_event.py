from lpdm_base_event import LpdmBaseEvent

class LpdmBuyPowerPriceEvent(LpdmBaseEvent):
    """A power source notifies a grid controller the price threshold for buying back power"""
    def __init__(self, source_device_id, target_device_id, time, value):
        LpdmBaseEvent.__init__(self, source_device_id, target_device_id, time, value)
        self.event_type = "buy_power_price"

