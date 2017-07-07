#Device.py

"""

A device maintains an events[] array, which are events to be processed. An EVENT has two components, a time signature and a eventtype. 
The queue is a heap sorted by by time signature, with time in milliseconds from the current time for the event to be processed. 








"""