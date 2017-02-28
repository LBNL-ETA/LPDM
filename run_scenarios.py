import os
import sys
import json
import pkgutil
import importlib

import summary_functions
from shutil import copyfile
from tug_simulation import TugSimulation

scenarios_path = 'scenarios'

file_list = sys.argv[1:] if len(sys.argv) > 1 else None
verbose = False
if file_list and "-v" in file_list:
    verbose = True
    file_list.remove("-v")

# go through each file in the scenarios path
for file in os.listdir(scenarios_path):
    if os.path.isfile(os.path.join(scenarios_path, file)):
        print file
        with open(os.path.join(scenarios_path, file)) as json_file:
            # load the scenario json file

            if not file_list or file in file_list:
                data = json.load(json_file)
                print data

                # set the headless flag to True
                data["headless"] = True
                data["verbose_logging"] = verbose
                sim = TugSimulation(data)
                sim.run()

                sim_path =  sim.simulation_log_manager.simulationLogPath()

                #copy the config file to the log file path
                copyfile(os.path.join(scenarios_path, file), os.path.join(sim_path, file))

                # load each summary function and process each log file with it
                for name in [name for _, name, _ in pkgutil.iter_modules(['summary_functions'])]:
                    # don't process the base class
                    if name != "summary_function_base":
                        summary_module  = importlib.import_module("summary_functions." + name)
                        for log_file in os.listdir(sim_path):
                            summary_module.run(sim_path, log_file)
