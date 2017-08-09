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

"""Runs the simulation."""

from Build.supervisor import Supervisor
import json
import logging


def read_config_file(filename):
    with open(filename, 'w') as config_file:
        scenario = json.load(config_file)
    return scenario

def setup_logging():
    logging.basicConfig(filename="simulation_results.log", level=logging.DEBUG)


## Reads in the simulation file. For each device,
#
def setup_simulation(supervisor):
    scenario = read_config_file("shared_test_scenario_1.txt")
    devices = scenario['devices']
    device_sections = ["grid_controllers", "power_sources", "euds"] # temporary. Will modify this structure.
    for section in device_sections:
        for device_list in scenario["devices"][section]:
            for device in device_list:
                # initialize that device. How do you know type? He used some kind
                # register with supervisor



    # (1) Initialize all Devices
    # (2) Set all Device's queues with their scheduled events
    # (3)


def run_simulation():
    supervisor = Supervisor()
    setup_simulation(supervisor)
    while supervisor.has_next_event():
        supervisor.occur_next_event()
    supervisor.finish_all()
    print("Simulation has finished.")

if __name__ == "__main__":
    run_simulation()







