#Supervisor.py

import priority_queue
"""

############MORE DOCUMENTATION HERE#################################

The supervisor class maintains a sorted map of the times of all initial events, mapping to the event with that time.

"""
class Supervisor:
    #we want a priority queue here
    def __init__(self):
        self.time_queue = priority_queue()


