from device.base.lpdm_exception import LpdmBaseException

class LpdmBatteryNotDischarging(LpdmBaseException):
    """Attempt to stop discharging if it isn't actually discharging"""
    def __init__(self, value="Battery is not currently discharging"):
        LpdmBaseException.__init__(self, value)


