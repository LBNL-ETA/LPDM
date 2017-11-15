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
    Grid Equipment is a subset of all Devices that does not include EUD's.
    Currently, there is no specific functionality.
"""

from abc import ABCMeta

from Build.Objects.device import Device
from Build.Simulation_Operation.support import SECONDS_IN_DAY


class GridEquipment(Device, metaclass=ABCMeta):

    ##
    # Initializes a device class with the identical input parameters. This will still be an abstract class.
    def __init__(self, device_id, device_type, supervisor, time=0, msg_latency=0, schedule=None, multiday=0,
                 total_runtime=SECONDS_IN_DAY, connected_devices=None):
        super().__init__(device_id, device_type, supervisor, time, msg_latency, schedule, multiday,
                         total_runtime, connected_devices)

    # Grid equipment specific functionality of sending power messages when power flows are now occurring.
    def send_power_message(self, target_id, power_amt):
        pass


