

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
    Base class for power sources (diesel generator, battery, pv, ...)
"""
from device.device import Device
import logging
import pprint

class PowerSource(Device):
    """
    """

    def __init__(self, config = None):
        """
        """
        # call the super constructor
        Device.__init__(self, config)


    # def init(self):
        # """Run any initialization functions for the device"""
        # # Setup the next events for the device
        # self.set_target_refuel_time()
        # self.set_next_hourly_consumption_calculation_event()
        # self.set_next_reasses_fuel_change_event()
        # self.set_next_refuel_event()
        # self.set_initial_price_event()
        # self.calculate_next_ttie()

