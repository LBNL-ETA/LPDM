"""
Implementation of a PWM and beaglebone based EUD device.
"""

from eud import Eud
from fan_control import PWMfan
import logging

class PWMfan_eud(Eud, PWMfan):
	def __init__(self, config = None):

		# Call super constructor
		Eud.__init__(self, config)

		# Server on which WeMo connections are running
		self._login_at_ip  = config["login_at_ip"] if type(config) is dict and "login_at_ip" in config.keys() else "debiant@***REMOVED***"
		self._fan_speed    = config["fan_speed"] if type(config) is dict and "fan_speed" in config.keys() else 100
	
		# Call insight drivers constructor
		PWMfan.__init__(self, self._login_at_ip)

	# Override with device specific functions
	def turnOn(self, time):
		"Turns pwn fan to full duty cycle"
		self.set_fan_speed(self, "99")
		# call super
		Eud.turnOn(self, time)

	# Override for specific device
	def turnOff(self, time):
		"Turns pwm duty cycle to 0% duty cycle"
		# Please not, 0% does NOT turn off the fan. Fan can only be turned off by removing power.
		self.set_fan_speed(self, "1")
		# call super
		Eud.turnOff(self, time)

	# Override for specific device measurement of power level
	def calculateNewPowerLevel(self):
		"Sets the power level of the eud experimental interpolation"
		# From experiments, we know that peak power occurs at 100% duty when 
		# voltage is 12 volts and current is 0.25 amps. So, we can anticipate about
		# 4 watts peak power, scaled linearly 
		return self._fan_speed * 4 / 100

	# Override for dimming features
	def onPriceChange(self, source_device_id, target_device_id, time, new_price):
		"Sets fan speed linearly according to current price, with 70 cents high, 30 cents low"

		if new_price < 30:
			self._fan_speed = 99;
		elif new price < 70	
			self._fan_speed = 99 - (new_price - 30) * 99 / 40

		# Call super
		Eud.onPriceChange(self, source_device_id, target_device_id, time, new_price)