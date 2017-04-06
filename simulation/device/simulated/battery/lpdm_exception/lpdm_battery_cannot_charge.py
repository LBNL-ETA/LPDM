from device.base.lpdm_exception import LpdmBaseException

class LpdmBatteryCannotCharge(LpdmBaseException):
    """An attempt was made to charge the battery before its ok_to_charge flag was set to True"""
    def __init__(self, value="Attempt to charge the battery without setting the ok_to_charge flag to True"):
        LpdmBaseException.__init__(self, value)

