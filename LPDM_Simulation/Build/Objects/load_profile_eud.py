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

""" An EUD which has a pre-defined load profile from an external data source """

from Build.Objects.eud import Eud
from Build.Simulation_Operation.support import SECONDS_IN_DAY
from Build.Simulation_Operation.event import Event

class LoadProfile(Eud):

    ##
    # @param power_level_list is a list of tuples of time, power_level.
    def __init__(self, device_id, supervisor, total_runtime, modulation_interval, power_level_list,
                 schedule=None, multiday=0, time=0, msg_latency=0):
        super().__init__(device_id=device_id, device_type="fixed_consumption", supervisor=supervisor,
                         time=time, msg_latency=msg_latency, schedule=schedule,
                         total_runtime=total_runtime, multiday=multiday, modulation_interval=modulation_interval)
        self._desired_power_level = 0
        self.setup_power_schedule(power_level_list, total_runtime)

    ##
    # Sets the device's power levels according to a schedule.
    # @param power_level_list list of time, power_level tuples
    # @param total_runtime how long the EUD is running for.
    def setup_power_schedule(self, power_level_list, total_runtime):
        curr_day = 0  # Current day in seconds. Starts at 0.
        while curr_day < total_runtime:
            for time, power_level in power_level_list:
                power_event = Event(self.set_desired_power_level)
                self.add_event(power_event, time + curr_day)
            curr_day += SECONDS_IN_DAY

    def set_desired_power_level(self, power_level):
        self._desired_power_level = power_level

    ##
    # Always returns the device's current desired power level based on its schedule
    def calculate_desired_power_level(self):
        return self._desired_power_level

    ##
    # No internal operation recorded
    def begin_internal_operation(self):
        pass


    ##
    # No internal operation recorded
    def end_internal_operation(self):
        pass

    ##
    # No need for internal state
    def update_state(self):
        pass

    ##
    # If the fixed consumption does not receive all the power it would like, it simply continues to operate at the
    # lower specified level.
    def respond_to_power(self, received_power):
        pass

    def device_specific_calcs(self):
        pass