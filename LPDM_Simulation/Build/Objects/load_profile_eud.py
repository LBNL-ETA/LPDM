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

import os
from Build.Objects.eud import Eud
from Build.Simulation_Operation.support import SECONDS_IN_DAY
from Build.Simulation_Operation.event import Event

class LoadProfile(Eud):

    ##
    # @param power_level_list is a list of tuples of time, power_level.
#     def __init__(self, device_id, supervisor, total_runtime, modulation_interval, power_level_list,
#                  schedule=None, multiday=0, time=0, msg_latency=0):
#         super().__init__(device_id=device_id, device_type="fixed_consumption", supervisor=supervisor,
#                          time=time, msg_latency=msg_latency, schedule=schedule,
#                          total_runtime=total_runtime, multiday=multiday, modulation_interval=modulation_interval)
#         self._desired_power_level = 0
#         self.setup_power_schedule(power_level_list, total_runtime)

    ##
    # @param data_filename is a the name of the load profile csv data file
    def __init__(self, device_id, supervisor, total_runtime, modulation_interval, data_filename,
                 schedule=None, multiday=0, time=0, msg_latency=0):
        super().__init__(device_id=device_id, device_type="fixed_consumption", supervisor=supervisor,
                         time=time, msg_latency=msg_latency, schedule=schedule,
                         total_runtime=total_runtime, multiday=multiday, modulation_interval=modulation_interval)
        self._desired_power_level = 0
        power_level_list = self.read_load_data(data_filename)
        self.setup_power_schedule(power_level_list, total_runtime)

    ##
    # Sets the device's power levels according to a schedule.
    # @param power_level_list list of time, power_level tuples
    # @param total_runtime how long the EUD is running for.
    def setup_power_schedule(self, power_level_list, total_runtime):
        # Check if power level list spans multiple days, or is single day repeat
        multiday_input = False
        for time, power_level in power_level_list:
            if time > 86400:
                multiday_input = True
                break
        if multiday_input: # multiple day power level list
            for time, power_level in power_level_list:
                power_event = Event(self.set_desired_power_level, power_level)
                self.add_event(power_event, time)
        else: # single day repeated power level list
            curr_day = int(self._time / SECONDS_IN_DAY)  # Current day in seconds
            while curr_day < total_runtime:
                for time, power_level in power_level_list:
                    power_event = Event(self.set_desired_power_level)
                    self.add_event(power_event, time + curr_day)
                curr_day += SECONDS_IN_DAY

    ##
    # Reads in the load profile csv data containing information about the power used at different times during
    # the simulation.
    # @param filename the input filename containing a list of times and associated power
    # @return a list of tuples of time (seconds), and power produced (watts).
    def read_load_data(self, filename):
        data_out = []  # list of tuples of time and power ratios
        pv_data = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                               "scenario_data/load_profiles/{}".format(filename))
        with open(pv_data, 'r') as data:
            DATASTART = 0
            TIMEIND = 0
            DCPOWERIND = 1
            for i, line in enumerate(data):
                if i < DATASTART:
                    continue
                parts = line.strip().split(',')
                if len(parts) >= DCPOWERIND + 1 and parts[0].strip():
                    time_parts = parts[0].split(':')
                    if len(time_parts) == 3: # Parse time from H:M:S format
                        time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
                    else: # Get time from row index, hourly increments
                        time_secs = (i - DATASTART)*3600
                    power = float(parts[DCPOWERIND])
                    data_out.append((time_secs, power))
        return data_out
        
    ##
    # Set device's desired power level, and use modulate_power() to send a request
    def set_desired_power_level(self, power_level):
        self._desired_power_level = power_level
        self.modulate_power()

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