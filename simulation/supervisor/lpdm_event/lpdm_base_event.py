class LpdmBaseEvent(object):
    def __init__(self, source_device_id=None, target_device_id=None, time=None, value=None):
        self.source_device_id = source_device_id
        self.target_device_id = target_device_id
        self.time = time
        self.value = value
        self.event_type = None

    def __repr__(self):
        return "type= {}, source = {}, target = {}, time={}, value = {}".format(
            self.event_type, self.source_device_id, self.target_device_id, self.time,  self.value
        )

    def __eq__(self, other):
        """
        Two events are equal if all properties are equal, except for the 'value'
        """
        return self.time == other.time \
                and self.event_type == other.event_type \
                and self.source_device_id == other.source_device_id \
                and self.target_device_id == other.target_device_id
