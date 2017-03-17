

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

import os
import re
import pprint
import random
import json
import logging
from supervisor import Supervisor
from simulation_logger import SimulationLogger

class Simulation(object):
    def __init__(self):
        self.config = None

    def load_config(self, file_name):
        with open(file_name) as config_file:
            self.config = json.load(config_file)

    def init_logger(self):
        self.log_manager = SimulationLogger(
            console_log_level=self.config.get("console_log_level", logging.DEBUG),
            file_log_level=self.config.get("file_log_level", logging.DEBUG),
            pg_log_level=self.config.get("pg_log_level", logging.DEBUG),
            log_to_postgres=self.config.get("log_to_postgres", False),
            log_format=self.config.get("log_format", None)
        )
        self.log_manager.init()

    def run(self):
        supervisor = Supervisor()
        supervisor.load_config(self.config)

        supervisor.run_simulation()

if __name__ == "__main__":
    sim = Simulation()
    sim.load_config("scenarios/scenario.json")
    sim.init_logger()
    sim.run()
