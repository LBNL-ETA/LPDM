########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""


"""

from Build.device import Device
from Build.eud import Eud


class Light(Eud):

    def __init__(self, device_id, supervisor):
        super().__init__(device_id, "light", supervisor)
        self._power_level_max = 100.0  # percent of power level to operate when
        self._power_level_low = 20.0  # percent of power level to operate when price is high.
        self._power_level = 0.0

    ## Will need to implement modulate power, which will involve sending a request message once
    # it determines that it needs a set amount of power.

    def turn_on(self):
        pass

    def turn_off(self):
        pass

    ##
    # Calculate the desired power level based on the price. Port this in.
    #
    def calculate_desired_power_level(self):
        pass

    def modulate_power(self):
        power_seek = self.calculate_desired_power_level()
        self.send_power_message("gc1", power_seek) # for now. Soon it will be allocate request.





