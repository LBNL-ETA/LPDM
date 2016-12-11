

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
import coloredlogs

class SimulationLogger:
    def __init__(self, verbose=True):
        self.app_name = "tug"
        self.base_path = "logs"
        self.folder = None
        self.log_id = None
        self.logger = None
        self.verbose = verbose

        self.generateSimulationId()
        self.createSimulationLogFolder()
        self.createSimulationLogger()

    def generateSimulationId(self):
        """build a unique id for each simulation"""
        max_id = 0
        for dirname in os.listdir(self.base_path):
            if re.match(r'^simulation_(\d+)$', dirname):
                parts = dirname.split("_")
                current_id = int(parts[1])
                if current_id > max_id:
                    max_id = current_id

        self.log_id = max_id + 1

    def simulationLogPath(self):
        if self.log_id is None:
            raise Exception("Simulation id has not been set.")
        else:
            return os.path.join(self.base_path, "simulation_{}".format(self.log_id))

    def createSimulationLogFolder(self):
        os.mkdir(self.simulationLogPath())

    def appName(self):
        return "{}_{}".format(self.app_name, self.log_id)

    def createSimulationLogger(self):
        self.logger = logging.getLogger(self.appName())
        self.logger.setLevel(logging.DEBUG)
        # coloredlogs.install(level='INFO', logger=logger)

        # create file handler which logs even debug messages
        fh = logging.FileHandler(os.path.join(self.simulationLogPath(), 'app.log'), mode='w')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        colored_formatter = coloredlogs.ColoredFormatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
        ch.setFormatter(colored_formatter)
        fh.setFormatter(formatter)

        # add the handlers to logger
        if self.verbose:
            self.logger.addHandler(ch)
        self.logger.addHandler(fh)

