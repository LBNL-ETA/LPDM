"""An event is modelled as a function and a series of arguments to be passed into that function. """


class Event:

    def __init__(self, action, args):
        self._action = action
        self._args = args

    def run_event(self):
        self._action(*self._args)
