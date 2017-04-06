
class LpdmBaseException(object):
    """Base class for LPDM simulation exceptions"""

    def __init__(self, description="Error"):
        self.name = "LPDM Exception"
        self.description = description

    def __repr(self):
        return "{}: {}".format(self.name, self.description)
