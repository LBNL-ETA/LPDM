

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
from supervisor.lpdm_event import LpdmBuyPowerPriceEvent
from device.base.power_source import PowerSource

class PowerSourceBuyer(object):
    """
    Represents a power source that can buy back power from the grid.
    """
    pass
