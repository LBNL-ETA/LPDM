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
