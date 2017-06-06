from device.base.lpdm_exception import LpdmBaseException

class LpdmScheduleInvalid(LpdmBaseException):
    """Unable to parse a schedule item"""
    def __init__(self, value="Unable to parse a schedule item."):
        LpdmBaseException.__init__(self, value)

