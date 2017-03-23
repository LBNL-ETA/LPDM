from device.lpdm_exception import LpdmBaseException

class LpdmBatteryCannotDischarge(LpdmBaseException):
    """An attempt was made to add load to the battery before its ok_to_discharge flag was set to True"""
    def __init__(self, value="Attempt to add load to the battery without setting the ok_to_discharge flag to True"):
        LpdmBaseException.__init__(self, value)
