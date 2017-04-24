from lpdm_event import LpdmPowerEvent, LpdmPriceEvent

class EventManager(object):
    """
    Keeps track of events.
    Stores events in a regular list.
    New ttie events are added through the 'add' method.  The events are added to the list, then
    sorted by time.
    """
    def __init__(self):
        self.events = []

    def add(self, the_event):
        """Add lpdm events to the list"""
        self.events.append(the_event)

    def get(self):
        """
        Get the next ttie.
        The events are stored in order of next ttie so get the first element in the list
        """
        if len(self.events):
            return self.events.pop(0)
        else:
            return None


