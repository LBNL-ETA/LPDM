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
import sys
import re
import logging
import traceback
import ConfigParser
from pg_handler import PgHandler

class SimulationLogger:
    """
    This class sets up the logging and handlers for the simulation.
    """
    def __init__(self, console_log_level=logging.DEBUG, file_log_level=logging.DEBUG, pg_log_level=logging.DEBUG):
        self.app_name = "lpdm"
        self.base_path = "logs"
        self.folder = None
        self.log_id = None
        self.logger = None
        self.console_log_level = console_log_level
        self.file_log_level = file_log_level
        self.pg_log_level = pg_log_level

    def init(self):
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
        fh.setLevel(self.file_log_level)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(self.console_log_level)

        # add the formatters
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        # add the file and console loggeres
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

        # setup the database logger if there's a configuration file
        path = os.path.dirname(os.path.realpath(__file__))
        pg_config = os.path.join(path, 'pg.cfg')
        if os.path.exists(pg_config):
            try:
                config = ConfigParser.ConfigParser()
                config.read(pg_config)

                if config.get("postgres", "enabled"):
                    config = {
                        "pg_enabled": config.get("postgres", "enabled"),
                        "pg_host": config.get("postgres", "host"),
                        "pg_port": config.get("postgres", "port"),
                        "pg_dbname": config.get("postgres", "dbname"),
                        "pg_user": config.get("postgres", "user"),
                        "pg_pass": config.get("postgres", "pass"),
                        "pg_schema": config.get("postgres", "schema")
                    }
                    db_handler = PgHandler(config)
                    db_handler.connect()
                    db_handler.setLevel(self.pg_log_level)
                    self.logger.addHandler(db_handler)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
                self.logger.error("Unable to setup the postgres logger")
                self.logger.error("\n".join(tb))

