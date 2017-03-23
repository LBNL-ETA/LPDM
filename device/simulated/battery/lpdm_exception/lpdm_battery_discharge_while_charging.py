from device.lpdm_exception import LpdmBaseException

class LpdmBatteryDischargeWhileCharging(LpdmBaseException):
    """Battery was told to discharge while it is currently discharging"""
    def __init__(self, value="Cannot discharge device while it is set to charge."):
        LpdmBaseException.__init__(self, value)
