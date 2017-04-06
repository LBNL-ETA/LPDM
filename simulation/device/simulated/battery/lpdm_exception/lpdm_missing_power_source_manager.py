from device.base.lpdm_exception import LpdmBaseException

class LpdmMissingPowerSourceManager(LpdmBaseException):
    """Battery is missing the power source manager"""
    def __init__(self, value="Power source manager is missing."):
        LpdmBaseException.__init__(self, value)

