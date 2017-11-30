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

    def setup_power_schedule(self, power_profile, peak_power, total_runtime):
        curr_day = int(self._time / SECONDS_IN_DAY)  # Current day in seconds. Starts at the PV's initial time.
        while curr_day < total_runtime:
            for time, power_proportion in power_profile:
                power_event = Event(self.update_power_status, peak_power, power_proportion)
                self.add_event(power_event, time + curr_day)
            curr_day += SECONDS_IN_DAY

    ##
    # Always returns the device's fixed consumption levels
    def calculate_desired_power_level(self):
        return self._desired_power_level

    ##
    def begin_internal_operation(self):
        pass

    def end_internal_operation(self):
        pass

    def update_state(self):
        pass

    ##
    # If the fixed consumption does not receive all the power it would like, it simply continues to operate at the
    # lower specified level.
    def respond_to_power(self, received_power):
        pass

    def device_specific_calcs(self):
        pass