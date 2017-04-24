import os
import sys
import json
import pkgutil
import importlib

import summary_functions
from shutil import copyfile
from simulation import Simulation

scenarios_path = 'scenarios'

file_list = sys.argv[1:] if len(sys.argv) > 1 else None

# go through each file in the scenarios path
for file in os.listdir(scenarios_path):
    file_path = os.path.join(scenarios_path, file)
    if os.path.isfile(file_path):
        if not file_list or file in file_list:
            sim = Simulation()
            sim.load_config(file_path)
            sim.init_logger()
            sim.run()

            sim_path =  sim.log_manager.simulation_log_path()

            # #copy the config file to the log file path
            copyfile(os.path.join(scenarios_path, file), os.path.join(sim_path, file))

            # # load each summary function and process each log file with it
            # for name in [name for _, name, _ in pkgutil.iter_modules(['summary_functions'])]:
                # # don't process the base class
                # if name != "summary_function_base":
                    # summary_module  = importlib.import_module("summary_functions." + name)
                    # for log_file in os.listdir(sim_path):
                        # summary_module.run(sim_path, log_file)
