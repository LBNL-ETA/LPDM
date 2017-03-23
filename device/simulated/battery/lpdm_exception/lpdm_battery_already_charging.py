from device.base.lpdm_exception import LpdmBaseException

class LpdmBatteryAlreadyCharging(LpdmBaseException):
    """Attempted to charge battery while it is already charging"""
    def __init__(self, value="Attempt to charge the battery while it is already charging."):
        LpdmBaseException.__init__(self, value)
