
class LpdmTask(object):
    def __init__(self, ttie, value):
        self.ttie = ttie
        self.value = value

    def __repr__(self):
        return "Task: {} -> {}".format(self.ttie, self.value)
