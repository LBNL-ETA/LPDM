"""An event is modelled as a function call with a specified series of arguments.
Thus, it is some action that will be performed during the simulation.
The time of an event's execution is stored in the queue of devices"""


class Event:
    ##
    # Initialize an event with a function and arguments for that function
    # @param action a function with __no return type__ to be run in the event
    # @param args a tuple of arguments for the function

    def __init__(self, action, args):
        self._action = action
        self._args = args

    ##
    # Initialize an event with a function and arguments for that function
    # @param action a function to be run in the event
    # @param args a tuple of arguments for the function

    def run_event(self):
        self._action(*self._args)
