import itertools
import heapq

###MAINLY FROM PYTHON WEBSITE. UNDERSTAND THIS.
class PriorityQueue:

    REMOVED = '<removed-task>'  # placeholder for a removed task

    def __init__(self, items = None):
        self._pq = []  # list of entries arranged in a heap
        self._entry_finder = {}  # mapping of tasks to entries
        self._counter = itertools.count()  # unique sequence count

    def add_task(self, task, priority=0):
        'Add a new task or update the priority of an existing task'
        if task in self._entry_finder:
            self.remove_task(self, task)
        count = next(self._counter)
        entry = [priority, count, task]
        self._entry_finder[task] = entry
        heapq.heappush(self._pq, entry)

    def remove_task(self, task):
        'Mark an existing task as REMOVED.  Raise KeyError if not found.'
        entry = self._entry_finder.pop(task)
        entry[-1] = self.REMOVED

    def pop_task(self):
        'Remove and return the lowest priority task. Raise KeyError if empty.'
        while self._pq:
            priority, count, task = heapq.heappop(self._pq)
            if task is not self.REMOVED:
                del self._entry_finder[task]
                return task
        raise KeyError('pop from an empty priority queue')


