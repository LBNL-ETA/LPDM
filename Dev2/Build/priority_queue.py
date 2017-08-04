################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

"""
A priority queue implementing a queue of items sorted by priority.
Adapted from https://docs.python.org/2/library/heapq.html.
"""

import itertools
import heapq


class PriorityQueue:

    REMOVED = '<removed-task>'  # placeholder for a removed task

    def __init__(self):
        self._pq = []  # list of entries (priority, count, task) arranged in a heap
        self._entry_finder = {}  # mapping of tasks to entries
        self._counter = itertools.count()  # unique sequence count to be used as a tiebreaker comparison in heap

    def add(self, task, priority=0):
        """Add a new task or update the priority of an existing task"""
        if task in self._entry_finder:
            self.remove(task)
        count = next(self._counter)
        entry = [priority, count, task]
        self._entry_finder[task] = entry
        heapq.heappush(self._pq, entry)

    def remove(self, task):
        """Mark an existing task as REMOVED.  Raise KeyError if not found."""
        entry = self._entry_finder.pop(task)
        entry[-1] = self.REMOVED

    def pop(self):
        """Remove and return the lowest priority task and its priority. Raise KeyError if empty."""
        while self._pq:  # Must loop in case front of queue is 'removed'
            priority, count, task = heapq.heappop(self._pq)
            if task is not self.REMOVED:
                del self._entry_finder[task]
                return task, priority
        raise KeyError('pop from an empty priority queue')

    def peek(self):
        """Returns the lowest priority task and its priority without removing. Raise KeyError if empty."""
        while self._pq:  # Must loop in case front of queue is 'removed'
            priority, count, task = heapq.heappop(self._pq)
            if task is not self.REMOVED:
                put_back = [priority, count, task]
                heapq.heappush(self._pq, put_back)
                return task, priority
        raise KeyError('peek from an empty priority queue')

    def is_empty(self):
        return not self._pq

    def clear(self):
        """clear the priority queue"""
        self._pq.clear()
        self._entry_finder.clear()
        self._counter = itertools.count()

    def shift(self, offset):
        """Shifts all the priorities of the priority queue __down__ by a specified offset"""
        for entry in self._pq:
            entry[0] -= offset
            if entry[0] < 0:
                print("Warning: Attempted To Set Priority For Task {} To Below Zero".format(entry[-1]))
                entry[0] = 0

