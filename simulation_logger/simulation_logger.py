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
import logging
from pg_handler import PgHandler

class SimulationLogger:
    """
    This class sets up the logging and handlers for the simulation.
    """
    def __init__(self, verbose=True):
        self.app_name = "lpdm"
        self.base_path = "logs"
        self.folder = None
        self.log_id = None
        self.logger = None
        self.verbose = verbose

    def initialize_logging(self):
        """Setup the log paths and create the logging handlers"""
        self.generate_simulation_id()
        self.create_simulation_log_folder()
        self.create_simulation_logger()

    def generate_simulation_id(self):
        """build a unique id for each simulation"""
        max_id = 0
        for dirname in os.listdir(self.base_path):
            if re.match(r'^simulation_(\d+)$', dirname):
                parts = dirname.split("_")
                current_id = int(parts[1])
                if current_id > max_id:
                    max_id = current_id

        self.log_id = max_id + 1

    def simulation_log_path(self):
        if self.log_id is None:
            raise Exception("Simulation id has not been set.")
        else:
            return os.path.join(self.base_path, "simulation_{}".format(self.log_id))

    def create_simulation_log_folder(self):
        os.mkdir(self.simulation_log_path())

    def app_name(self):
        return "{}_{}".format(self.app_name, self.log_id)

    def create_simulation_logger(self):
        """
        Create the loggers and handlers for the app.
        Create an app level logger that stores log messages for the entire app.
        Next create a console handler to print output to the console.
        Create handler for writing log messages to Postgres
        """
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.DEBUG)

        # setup the formatter
        formatter = logging.Formatter('[%(relativeCreated)d-%(threadName)s-%(filename)s-%(funcName)s-%(lineno)d] - %(message)s')

        # create file handler which logs even debug messages
        fh = logging.FileHandler(os.path.join(self.simulation_log_path(), 'app.log'), mode='w')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # colored_formatter = coloredlogs.ColoredFormatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # create formatter and add it to the handlers
        # formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # setup the database logger
        config = {
            "pg_enabled": True,
            "pg_host": "172.22.0.2",
            "pg_port": "5432",
            "pg_dbname": "lpdm",
            "pg_user": "docker",
            "pg_pass": "q^r+_#H=9fz&yGJ8",
            "pg_schema": "mikey2"
        }
        db_handler = PgHandler(config)
        db_handler.connect()
        db_handler.setLevel(logging.DEBUG)

        # add the handlers to logger
        # if self.verbose:
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)
        self.logger.addHandler(db_handler)

