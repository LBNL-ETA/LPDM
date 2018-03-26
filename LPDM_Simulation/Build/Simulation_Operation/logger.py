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

import os
import sys
import re
import logging
from datetime import datetime, timezone

from Build.Simulation_Operation.support import SECONDS_IN_DAY, SECONDS_IN_HOUR, SECONDS_IN_MINUTE


"""
Sets up the logging functionality for the entire simulation, creating the necessary directory, 
establishes the streams to the console and file, sets the output text format, and writes header information. 
"""


class SimulationLogger:

    def __init__(self, console_log_level=logging.INFO, file_log_level=logging.DEBUG,
                 database_log_level=logging.DEBUG, log_to_database=False):
        self.app_name = "lpdm"
        self.base_path = os.path.join(
                         os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "logs")
        self.folder = None  #
        self.log_id = None  # The unique number associated with this log to generate a unique folder
        self.logger = None
        self.console_log_level = console_log_level  # Level of information to include in the console stream
        self.file_log_level = file_log_level  # Level of information to include in the local file stream
        self.database_log_level = database_log_level  # Level of information to include in the postgres database stream
        self.log_to_database = log_to_database  # Whether to log to remote postgres database

    ##
    # Creates a unique folder for this simulation log, and then sets up the streams
    # to the console, file, and database for all log messages.
    # @param config_file the the name of the input JSON specifying the logging levels we will use
    # @param override_args a list of override arguments provided as arguments to log at the top of file

    def initialize_logging(self, config_file, override_args):
        self.generate_log_id()
        self.create_simulation_log_folder()
        self.create_simulation_logger(config_file, override_args)

    ##
    # Searches through all of the existing log folder names and finds a unique simulation ID to use for this logging
    # session, to avoid overwriting files.

    def generate_log_id(self):
        max_id = 0
        for dirname in os.listdir(self.base_path):
            if re.match(r'^simulation_(\d+)$', dirname):
                parts = dirname.split("_")
                current_id = int(parts[1])
                if current_id > max_id:
                    max_id = current_id

        self.log_id = max_id + 1

    ##
    # Returns the directory path of the where the simulation log will output to
    def simulation_log_path(self):
        if self.log_id is None:
            raise Exception("Simulation id has not been set.")
        else:
            return os.path.join(self.base_path, "simulation_{}".format(self.log_id))

    ##
    # Makes the folder for the simulation log
    def create_simulation_log_folder(self):
        os.mkdir(self.simulation_log_path())

    ##
    # A custom logging formatter which for the first time it is called, prepends a header to the file,
    # before switching back to the original format style.
    class FormatterWithHeader(logging.Formatter):
        def __init__(self, header, fmt=None, datefmt=None, style='%'):
            super().__init__(fmt, datefmt, style)
            self.header = header
            # Override the normal format method
            self.format = self.first_line_format

        def first_line_format(self, record):
            # Revert to original file format
            self.format = super().format
            return self.header + "\n" + self.format(record)

    ##
    # Creates the simulation logger by
    # @param config_file the name of configuration file, to be included in the top of the simulation description.
    # @param override_args an optional list override arguments to include in the header of the file

    def create_simulation_logger(self, config_file, override_args=None):

        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(logging.DEBUG)  # Set debug as minimum logging level. Debug and higher can be logged.

        # Create the header to include at the top of the file
        if override_args:
            # Record override arguments at top of file in addition to input JSON and time
            log_override_vals = "Override values: {}".format(", ".join(override_args))
            header = "{}\n{}\n{}\n".format(datetime.now(timezone.utc).astimezone().isoformat(),
                                           config_file, log_override_vals)
        else:
            header = "{}\n{}\n".format(datetime.now(timezone.utc).astimezone().isoformat(), config_file)

        # create file handler for the output log file
        fh = logging.FileHandler(os.path.join(self.simulation_log_path(), 'sim_results.log'), mode='w')
        fh.setLevel(self.file_log_level)

        # create console handler for the console log messages
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.console_log_level)

        fmt = '%(message)s'

        ch.setFormatter(self.FormatterWithHeader(header=header, fmt=fmt))
        fh.setFormatter(self.FormatterWithHeader(header=header, fmt=fmt))

        # add the file and console loggers
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)





