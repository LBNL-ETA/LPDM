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
from datetime import datetime, timezone


class SimulationLogger:

    """
    This class sets up the logging and handlers for the simulation.
    """
    def __init__(self, console_log_level=logging.DEBUG, file_log_level=logging.DEBUG, pg_log_level=logging.DEBUG,
                 log_to_postgres=False, log_format=None):
        self.app_name = "lpdm"
        self.base_path = "../logs"
        self.folder = None
        self.log_id = None
        self.logger = None
        self.console_log_level = console_log_level
        self.file_log_level = file_log_level
        self.pg_log_level = pg_log_level
        self.log_to_postgres = log_to_postgres
        self.log_format = log_format

    ##
    # Setup the logpaths and creates the logging handlers.
    def init(self, config_file, override_args):
        """Setup the log paths and create the logging handlers"""
        self.generate_simulation_id()
        self.create_simulation_log_folder()
        self.create_simulation_logger(config_file, override_args)

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

    ##
    # Class to add a header to the python logger. Creates a custom formatter for first line then switches back.

    class FileHandlerWithHeader(logging.FileHandler):
        def __init__(self, header, filename, mode='a', encoding=None, delay=False):
            super().__init__(filename, mode, encoding, delay)
            self.header = header
            self.file_pre_exists = os.path.exists(filename)

            # Write the header if delay is False and a file stream was created.
            if not delay and self.stream is not None:
                self.stream.write("{}\n".format(self.header))

        def emit(self, record):
            if self.stream is None:
                self.stream = self._open()
            if not self.file_pre_exists:
                self.stream.write("{}\n".format(self.header))
            super().emit(record)

    def create_simulation_logger(self, config_file, override_args):
        """
        Create the loggers and handlers for the app.
        Create an app level logger that stores log messages for the entire app.
        Next create a console handler to print output to the console.
        Create handler for writing log messages to Postgres
        """
        self.logger = logging.getLogger(self.app_name)
        # the handlers won't be able to log anything lower than this log value
        # so set to the lowest (logging.DEBUG)
        self.logger.setLevel(logging.DEBUG)

        # setup the formatter
        if len(override_args):
            log_override_vals = "Override values: {}".format(", ".join(override_args))
            header = "{}\n{}\n{}\n".format(datetime.now(timezone.utc).astimezone().isoformat(), config_file,
                                           log_override_vals)
        else:
            header = "{}\n{}\n".format(datetime.now(timezone.utc).astimezone().isoformat(), config_file)
        # create file handler which logs even debug messages
        fh = self.FileHandlerWithHeader(header, os.path.join(self.simulation_log_path(), 'sim_results.log'), mode='w')
        fh.setLevel(self.file_log_level)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(self.console_log_level)

        # add the formatters
        if self.log_format == "debug":
            fmt = '[%(relativeCreated)d-%(levelname)-s-%(threadName)s-%(filename)s-%(funcName)s-%(lineno)d] - %(message)s'
        else:
            fmt = '%(message)s'
        ch.setFormatter(logging.Formatter(fmt))
        fh.setFormatter(logging.Formatter(fmt))

        # add the file and console loggers
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)


