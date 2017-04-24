
class LpdmEvent(object):
    def __init__(self, ttie, value, name=None):
        self.ttie = ttie
        self.value = value
        self.name = name

    def __repr__(self):
        if self.name is None:
            return "Task: {} -> {}".format(self.ttie, self.value)
        else:
            return "Task {}: {} -> {}".format(self.name, self.ttie, self.value)
