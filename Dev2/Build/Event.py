"""LPDM event classes. Each device maintains a queue of events which it must process individually. 
An event has two components: a time stamp (which is time from current reference until that event must be processed, 
and a way of modif



"""

class Event:

	#must initialize with integer time stamp 
	def __init__(self, time):
		self._time_stamp = time

	def advanceTime(self):
		self._time_stamp -= 1


"""

An event for when the device receives a price change. 

"""


class PriceEvent(Event):
	def __init__(self, price_change, time = 0)



"""an event which describes a change in power flows, thus changing the net load on the device"""
class PowerEvent(Event): 

