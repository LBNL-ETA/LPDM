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

import json
import logging
from Build.simulation_logger import SimulationLogger

class Simulation:

    def __init__(self):
        self.end_time = 0 # time to run simulation until. Update in setup_simulation.
        self.log_manager = None
        self.config = None
        self.supervisor = None

    def read_config_file(self, filename):
        with open(filename, 'w') as config_file:
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

    ## Reads in the simulation file. For each device,
    #
    def setup_simulation(self):
        self.read_config_file("shared_test_scenario_1.txt")

        """We will change this later. Mike's way ain't bad (DeviceClassLoader)"""

        for gc in self.config["devices"]["grid_controllers"]:
            gc_id = gc['device_id']
            batt_info = gc['battery'] if 'battery' in gc.keys() else None
            battery = Battery(price_logic=None, capacity=batt_info['capacity']) if batt_info else None
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
            light = Light(light_id, self.supervisor)
            light_schedule = eud['schedule']
            light.setup_schedule(light_schedule)
            self.supervisor.register_device(light)

        days_to_run = int(self.config["run_time_days"])
        self.end_time = 24 * 60 * 60 * days_to_run  # end time in seconds

    def run_simulation(self):
        self.supervisor = Supervisor()
        self.setup_simulation()
        while self.supervisor.has_next_event():
            device_id, time_stamp = self.supervisor.peek_next_event()
            if time_stamp > self.end_time:
                break
            self.supervisor.occur_next_event()
        self.supervisor.finish_all(self.end_time)

if __name__ == "__main__":
    sim = Simulation()
    sim.run_simulation()







