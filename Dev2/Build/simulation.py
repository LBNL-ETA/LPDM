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
        self.end_time = 0  # time until which to run simulation. Update this in setup_simulation.
        self.log_manager = None
        self.config = None
        self.supervisor = None
        # A dictionary of eud class names and their respective constructor input names to read from json (in order)
        self.eud_dictionary = {
            'light': [Light, 'max_power_output'],
            'air_conditioner': [None, '']
        }

    def read_config_file(self, filename):
        with open(filename, 'r') as config_file:
            self.config = json.load(config_file)

    def setup_logging(self, config_file):
        self.log_manager = SimulationLogger(
            console_log_level=self.config.get("console_log_level", logging.DEBUG),
            file_log_level=self.config.get("file_log_level", logging.DEBUG),
            pg_log_level=self.config.get("pg_log_level", logging.DEBUG),
            log_to_postgres=self.config.get("log_to_postgres", False),
            log_format=self.config.get("log_format", None)
        )
        self.log_manager.init(config_file)

    def read_grid_controllers(self, config):

        # TODO: Incorporate their scheduling

        connections = []  # a list of tuples of (gc, [connections]) to initialize later once all devices are set.
        for gc in config['devices']['grid_controllers']:
            gc_id = gc['device_id']
            price_logic = gc['price_logic']
            # gc_uuid = gc.get(uuid, 0)
            msg_latency = gc.get('message_latency', 0)  # default 0 msg latency
            connected_devices = gc.get('connected_devices', None)
            if connected_devices:
                connections.append((gc_id, connected_devices))

            batt_info = gc.get('battery', None)
            if batt_info:
                batt_price_logic = batt_info['price_logic']
                batt_id = batt_info['battery_id']
                max_discharge_rate = batt_info.get('max_discharge_rate', 1000.0)
                max_charge_rate = batt_info.get('max_charge_rate', 1000.0)
                capacity = batt_info.get('capacity', 50000.0)
                battery = Battery(battery_id = batt_id, price_logic=batt_price_logic, capacity=capacity,
                                  max_charge_rate=max_charge_rate, max_discharge_rate=max_discharge_rate)
            else:
                battery = None
            self.supervisor.register_device(
                GridController(device_id=gc_id, supervisor=self.supervisor, battery=battery, msg_latency=msg_latency,
                               price_logic=price_logic))
        return connections

    def read_utility_meters(self, config):

        # TODO: Incorporate new scheduling

        connections = []  # a list of tuples of (utm, [connections]) to initialize later once all devices are set.
        for utm in config['devices']['utility_meters']:
            utm_id = utm['device_id']
            connected_devices = utm.get('connected_devices', None)
            if connected_devices:
                connections.append((utm_id, connected_devices))

            new_utm = UtilityMeter(utm_id, self.supervisor)
            utm_schedule = utm['schedule']
            utm_price_schedule = utm['price_schedule']
            new_utm.setup_schedule(utm_schedule)
            new_utm.setup_price_schedule(utm_price_schedule)
            self.supervisor.register_device(new_utm)
        return connections

    def read_pvs(self, config):
        pass
        # TODO: Once we implement PV etc.

    def read_euds(self, config):
        connections = []
        for eud in config['devices']['euds']:
            eud_id = eud['device_id']
            eud_type = eud['eud_type']
            connected_devices = eud.get('connected_devices', None)
            if connected_devices:
                connections.append((eud_id, connected_devices))

            eud_class = self.eud_dictionary[eud_type][0]
            # get all the arguments for the eud constructor
            args = [eud.get(cls_arg, None) for cls_arg in self.eud_dictionary[eud_type][1:]]
            new_eud = eud_class(eud_id, self.supervisor, *args)
            schedule = eud.get('schedule', None)
            if schedule:
                new_eud.setup_schedule(schedule)
            self.supervisor.register_device(new_eud)
        return connections

    ## Reads in the simulation json file.
    #
    #

    def setup_simulation(self, config_file):
        self.read_config_file("../scenario_data/{}".format(config_file))
        self.setup_logging(config_file)

        #  TODO: pv_connections = self.read_pvs(self.config)

        # reads in and creates all the simulation devices before registering them
        connections = [self.read_grid_controllers(self.config), self.read_utility_meters(self.config),
                       self.read_euds(self.config)]

        for connect_list in connections:
            for this_device_id, connects in connect_list:
                this_device = self.supervisor.get_device(this_device_id)
                for that_device_id in connects:
                    that_device = self.supervisor.get_device(that_device_id)
                    this_device.register_device(that_device, that_device_id, 1)
                    that_device.register_device(this_device, this_device_id, 1)

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


