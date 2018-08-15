########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""An event is modelled as a function call with a specified series of arguments,
which can then be run at any time. Objects which use Events are responsible for
maintaining knowledge of the specific time at which they want to run the Event.
"""


class Event(object):

    ##
    # Initialize an event with a function and arguments for that function
    # @param action a state-affecting function to be run in the event (function does not return a value).
    # @param args any number of arguments to pass into the function to pack into a tuple.

    def __init__(self, action, *args):
        self._action = action
        self._args = args

    ##
    # Initialize an event with a function and arguments for that function
    # @param action a function to be run in the event
    # @param args a tuple of arguments for the function

    def run_event(self):
        self._action(*self._args)

