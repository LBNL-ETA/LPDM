class LpdmBaseException(Exception):
    """Base exception class for LPDM"""
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.value)
