from device.base.lpdm_exception import LpdmBaseException

class LpdmBatteryAlreadyDischarging(LpdmBaseException):
    """Attempt to start battery discharge when already discharging"""
    def __init__(self, value="Battery is already set to discharge"):
        LpdmBaseException.__init__(self, value)



