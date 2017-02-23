class LpdmBaseEvent(object):
    def __init__(self, source_device_id=None, target_device_id=None, value=None):
        self.source_device_id = source_device_id
        self.target_device_id = target_device_id
        self.value = value
        self.event_type = None
