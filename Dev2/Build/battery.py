#Battery.py

"""A battery is a component of a grid controller which serves to balance its inflows and outflows
The Grid Controller thus has complete control over its battery(s), no messages are passed between them
but instead power flows are instantaneous.

Batteries encapsulate this behavior of a Grid Controller:


. """

from enum import Enum


class Battery(object):


    ##
    # Starting charge is the beginning battery state of the Battery, between 0 and 100 inclusive.
    # Charging preference is either positive (discharge), 0 (neutral), and -1 (charge).

    def __init__(self, battery_num, starting_charge = 50):

        self._charging_preference = BatteryChargingPreference.NEUTRAL
        self._preferred_charge_rate = 0
        self._preferred_discharge_rate = 0
        self._max_charge_rate = 0
        self._max_discharge_rate = 0


class BatteryChargingPreference(Enum):
    DISCHARGE = -1
    NEUTRAL = 0
    CHARGE = 1

print(BatteryChargingPreference.DISCHARGE.value)

