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

from Build.grid_controller import GridController

from Build.battery import Battery
from Build.utility_meter import UtilityMeter
from Build.light import Light
from Build.simulation_logger import SimulationLogger

import json
import logging
import sys


class Simulation:

    def __init__(self):
        self.end_time = 0 # time to run simulation until. Update in setup_simulation.
        self.log_manager = None
        self.config = None
        self.supervisor = None

    def read_config_file(self, filename):
        with open(filename, 'r') as config_file:
            self.config = json.load(config_file)

    def setup_logging(self):
        self.log_manager = SimulationLogger(
            console_log_level=self.config.get("console_log_level", logging.DEBUG),
            file_log_level=self.config.get("file_log_level", logging.DEBUG),
            pg_log_level=self.config.get("pg_log_level", logging.DEBUG),
            log_to_postgres=self.config.get("log_to_postgres", False),
            log_format=self.config.get("log_format", None)
        )
        self.log_manager.init()

    ## Reads in the simulation json file.
    #
    #

    def setup_simulation(self, config_file):
        self.read_config_file("../scenario_data/{}".format(config_file))
        self.setup_logging()

        """We will change this later. Mike's way ain't bad (DeviceClassLoader).
        Want to change the references to so that the connected_devices can be done properly"""

        for gc in self.config["devices"]["grid_controllers"]:
            gc_id = gc['device_id']
            batt_info = gc.get('battery', None)
            if batt_info:
                max_discharge_rate = batt_info.get('max_discharge_rate', 1000.0)
                max_charge_rate = batt_info.get('max_charge_rate', 1000.0)
                capacity = batt_info.get('capacity', 50000.0)
                battery = Battery(price_logic=None, capacity=capacity, max_charge_rate=max_charge_rate,
                                  max_discharge_rate=max_discharge_rate)
            else:
                battery = None
            self.supervisor.register_device(GridController(gc_id, self.supervisor, battery=battery))
        for power_source in self.config["devices"]["power_sources"]:
            utm_id = power_source['device_id']
            utm = UtilityMeter(utm_id, self.supervisor)
            utm_schedule = power_source['schedule']
            utm_price_schedule = power_source['price_schedule']
            utm.setup_schedule(utm_schedule)
            utm.setup_price_schedule(utm_price_schedule)
            self.supervisor.register_device(utm)
        for eud in self.config["devices"]["euds"]:
            light_id = eud['device_id']
            max_power = eud['max_power_output']
            light = Light(device_id=light_id, supervisor=self.supervisor, max_operating_power=max_power)
            light_schedule = eud['schedule']
            light.setup_schedule(light_schedule)
            self.supervisor.register_device(light)

        gc1 = self.supervisor.get_device("gc_1")
        utm1 = self.supervisor.get_device("utm_1")
        eud1 = self.supervisor.get_device("eud_1")
        gc1._connected_devices["utm_1"] = utm1
        gc1._connected_devices["eud_1"] = eud1
        utm1._connected_devices["gc_1"] = gc1
        eud1._connected_devices["gc_1"] = gc1

        #gc1.engage([utm1, eud1])  # registers the gc with these entities and vice versa.

        days_to_run = int(self.config["run_time_days"])
        self.end_time = 24 * 60 * 60 * days_to_run  # end time in seconds

    def run_simulation(self, config_file):
        self.supervisor = Supervisor()
        self.setup_simulation(config_file)
        while self.supervisor.has_next_event():
            device_id, time_stamp = self.supervisor.peek_next_event()
            if time_stamp > self.end_time:
                break
            self.supervisor.occur_next_event()
        self.supervisor.finish_all(self.end_time)

if __name__ == "__main__":
    sim = Simulation()
    if len(sys.argv) >= 2:
        sim.run_simulation(sys.argv[1])
    else:
        raise FileNotFoundError("Must enter a configuration filename")

# Use scenario_A_basic_discharge_only.json" as parameter


