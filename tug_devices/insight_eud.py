

################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0" 
# Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory 
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact 
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

"""
Implementation of a WeMo Insight based EUD device
"""

from eud import Eud
from wemo_control.wemo_switch import WemoInsight


class InsightEud(Eud):
    def __init__(self, config=None):

        # Call super constructor
        Eud.__init__(self, config)

        # Device name on as supplied by WeMo
        self._insight_name = config["insight_name"] if type(config) is dict and "insight_name" in config.keys() else "WeMo Insight"

        # Server on which WeMo connections are running
        self._insight_server_url = config["insight_server_url"] if type(config) is dict and "insight_server_url" in config.keys() else "***REMOVED***"

        # Build hardware link
        self._insight = WemoInsight(self._insight_name, self._insight_server_url)

    # Override with device specific functions
    def turnOn(self):
        "Turns device attached to insight on"
        self._insight.on()
        # call super
        Eud.turnOn(self)

    # Override for specific device
    def turnOff(self):
        "Turns device attached to Insight off"
        print('*******turn off insight*******')
        self._insight.off()
        # call super
        Eud.turnOff(self)

    # Override for specific device measurement of power level
    # def calculateNewPowerLevel(self):
    #     "Sets the power level of the eud based on insight measurement"
        # Insight knows!
        # return self.current_power()

    # Override for specific device measurement and accounting for varying power
    # def setPowerLevel(self):
    #     "Set the power level of the Insight eud (W). If consumption has changed by more than 5%, broadcast new power level"
    #     new_power = self.calculateNewPowerLevel()
    #     # Check for a 5% change, otherwise there is no real change
    #     if abs(new_power - self._power_level) / self._power_level * 100 == 5:
    #         self._power_level = new_power

    #         # Round to 0
    #         if abs(self._power_level) == 0:
    #             self._in_operation = False
    #         elif self._power_level > 0 and not self._in_operation:
    #             self._in_operation = True

    #         # Broadcast behavior
    #         self.tugLogAction(action="set_power_level", is_initial_event=False, value=self._power_level, description='W')
    #         self.broadcastNewPower(new_power)
