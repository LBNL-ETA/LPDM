"""
Implementation of a WeMo Insight based EUD device
"""

from eud import Eud
from wemo_switch import WemoInsight
import logging

class InsightEud(Eud):
	def __init__(self, config = None):

		# Call super constructor
		Eud.__init__(self, config)

		# Device name on as supplied by WeMo
		self._insight_name    = config["insight_name"] if type(config) is dict and "insight_name" in config.keys() else "WeMo Insight"
		
		# Server on which WeMo connections are running
		self._insight_server_url  = config["insight_server_url"] if type(config) is dict and "insight_server_url" in config.keys() else "192.168.1.3"
		
		# Call insight drivers constructor
		WemoInsight.__init__(self, self._insight_name, self._insight_server_url)

	# Override with device specific functions
	def turnOn(self, time):
		"Turns device attached to insight on"
		self.on()
		# call super
		Eud.turnOn(self, time)

	# Override for specific device
	def turnOff(self, time):
		"Turns device attached to Insight off"
		self.off()
		# call super
		Eud.turnOff(self, time)

	# Override for specific device measurement of power level
	def calculateNewPowerLevel(self):
		"Sets the power level of the eud based on insight measurement"
		# Insight knows!
		return self.current_power()

	# Override for specific device measurement and accounting for varying power
	def setPowerLevel(self):
		"Set the power level of the Insight eud (W). If consumption has changed by more than 5%, broadcast new power level"
		new_power = self.calculateNewPowerLevel()
		# Check for a 5% change, otherwise there is no real change
		if abs(new_power - self._power_level) / self._power_level * 100 = 5:
			self._power_level = new_power

			# Round to 0
			if abs(self._power_level) == 0:
				self._in_operation = False
			elif self._power_level > 0 and not self._in_operation:
				self._in_operation = True

			# Broadcast behavior 
			self.tugLogAction(action="set_power_level", is_initial_event=False, value=self._power_level, description='W')
            self.broadcastNewPower(new_power)


