from event_manager import EventManager
from lpdm_event import LpdmTtieEvent

class TtieEventManager(EventManager):
    """
    Keeps track of ttie events.
    Stores events in a regular list.
    New ttie events are added through the 'add' method.  The events are added to the list, then
    sorted by time.
    """
    def add(self, lpdm_ttie_event):
        """Add a ttie event to the list"""

        # make sure parameter is correct type
        if isinstance(lpdm_ttie_event, LpdmTtieEvent):
            # store the ttie events in order by time
            if len(self.events):
                for i, e in enumerate(self.events):
                    # if the new event has a time that comes before the enumarted event then insert it into the list
                    if lpdm_ttie_event.value < e.value:
                        self.events.insert(i, lpdm_ttie_event)
                        return
            # if this section is reached then
            # 1) there are no events so just append to the end
            # or 2) there are events, but the new event is the farthest out in time so add it to the end of the list
            self.events.append(lpdm_ttie_event)
        else:
            raise Exception("TtieEventManager.add expects the parameter to be of type LpdmTtieEvent")
