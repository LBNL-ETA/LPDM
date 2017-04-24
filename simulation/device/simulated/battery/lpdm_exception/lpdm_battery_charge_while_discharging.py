from device.base.lpdm_exception import LpdmBaseException

class LpdmBatteryChargeWhileDischarging(LpdmBaseException):
    """Attempted to charge battery while there is a load on it"""
    def __init__(self, value="Attempt to charge the battery while it is currently discharging."):
        LpdmBaseException.__init__(self, value)
