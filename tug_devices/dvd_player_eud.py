"""
Implementation of a WeMo Insight based EUD device
"""

from eud import Eud
from tropec_hw_adapters_repo.global_cache_control.global_cache_controls import GlobalCacheBridge
from tropec_hw_adapters_repo.global_cache_control.dvd_controls import DVDController


class InsightEud(Eud):
    def __init__(self, config=None):

        # Call super constructor
        Eud.__init__(self, config)

        # Bridge IP address on Global Cache Device
        self._bridge_ipaddr = config["bridge_ipaddr"] if type(config) is dict and "bridge_ipaddr" in config.keys() else '***REMOVED***'

        # Number of emitter on Global Cache Device
        self._emitter_num = config["_emitter_num"] if type(config) is dict and "_emitter_num" in config.keys() else 1

        # Build hardware link
        self._bridge = GlobalCacheBridge(self._bridge_ipaddr)

        # Build Device connection
        self._dvd_player = DVDController(self._bridge, self._emitter_num)

    # Override with device specific functions
    def turnOn(self, time):
        "Turns device attached to insight on"
        # call super
        Eud.turnOn(self, time)
        if not self._in_operation:
            self._dvd_player.power()

    # Override for specific device
    def turnOff(self, time):
        "Turns device attached to Insight off"
        # call super
        Eud.turnOff(self, time)
        if self._in_operation:
            self._dvd_player.power()

    # Override for specific device measurement of power level
    def calculateNewPowerLevel(self):
        "Sets the power level of the eud based on insight measurement"
        # Fake number representing large usage
        if self._in_operation:
            return 20000
        else:
            return 0

    # Override for specific device measurement and accounting for varying power
    def setPowerLevel(self):
        "Set the power level EUD and broadcast the new power if it has changed"
        new_power = self.calculateNewPowerLevel()
        # Check if power has changed and adjust operation
        if not self._power_level == new_power:
            self._power_level = new_power
            if self._power_level == 0:
                self._in_operation = False
            elif self._power_level > 0 and not self._in_operation:
                self._in_operation = True

            # Broadcast behavior
            self.tugLogAction(action="set_power_level", is_initial_event=False, value=self._power_level, description='W')
            self.broadcastNewPower(new_power)
