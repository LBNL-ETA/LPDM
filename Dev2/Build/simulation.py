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


"""Performs FILE IO and sets up the simulation."""

from Build.supervisor import Supervisor
from Build.grid_controller import GridController

from Build.battery import Battery
from Build.utility_meter import UtilityMeter
from Build.light import Light
from Build.simulation_logger import SimulationLogger

import json
import logging
import sys
import os

class Simulation:

    def __init__(self):
        self.end_time = 0  # time until which to run simulation. Update this in setup_simulation.
        self.log_manager = None
        self.config = None
        self.supervisor = None
        # A dictionary of eud class names and their respective constructor input names to read from json (in order)
        self.eud_dictionary = {
            'light': [Light, 'max_operating_power'],
            'air_conditioner': [None, '']
        }

    def read_config_file(self, filename):
        with open(filename, 'r') as config_file:
            self.config = json.load(config_file)

    def setup_logging(self, config_file, override_args):
        self.log_manager = SimulationLogger(
            console_log_level=self.config.get("console_log_level", logging.DEBUG),
            file_log_level=self.config.get("file_log_level", logging.DEBUG),
            pg_log_level=self.config.get("pg_log_level", logging.DEBUG),
            log_to_postgres=self.config.get("log_to_postgres", False),
            log_format=self.config.get("log_format", None)
        )
        self.log_manager.init(config_file, override_args)

    ##
    #
    # @param runtime the length of running the simulation, used for GC's to setup their price calc schedules and
    def read_grid_controllers(self, config, runtime, override_args):

        connections = []  # a list of tuples of (gc, [connections]) to initialize later once all devices are set.
        for gc in config['devices']['grid_controllers']:
            gc_id = gc['device_id']
            price_logic = gc['price_logic']
            # gc_uuid = gc.get(uuid, 0)
            msg_latency = gc.get('message_latency', 0)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(gc_id), msg_latency))
            min_alloc_response_threshold = gc.get('threshold_alloc', 1)
            min_alloc_response_threshold = float(override_args.get('devices.{}.threshold_alloc'.format(gc_id),
                                                                   min_alloc_response_threshold))

            schedule = gc.get('schedule', None)
            connected_devices = gc.get('connected_devices', None)
            if connected_devices:
                connections.append((gc_id, connected_devices))

            batt_info = gc.get('battery', None)
            if batt_info:
                batt_price_logic = batt_info['price_logic']
                batt_id = batt_info['battery_id']
                max_discharge_rate = batt_info.get('max_discharge_rate', 1000.0)
                max_discharge_rate = float(override_args.get('devices.{}.{}.max_discharge_rate'.format(gc_id, batt_id),
                                                             max_discharge_rate))
                max_charge_rate = batt_info.get('max_charge_rate', 1000.0)
                max_charge_rate = float(override_args.get('devices.{}.{}.max_charge_rate'.format(gc_id, batt_id),
                                                          max_charge_rate))
                capacity = batt_info.get('capacity', 50000.0)
                capacity = float(override_args.get('devices.{}.{}.capacity'.format(gc_id, batt_id),
                                                   capacity))
                update_frequency = batt_info.get('update_frequency', 1200)
                battery = Battery(battery_id=batt_id, price_logic=batt_price_logic, capacity=capacity,
                                  max_charge_rate=max_charge_rate, max_discharge_rate=max_discharge_rate,
                                  update_frequency=update_frequency)
            else:
                battery = None

            new_gc = GridController(device_id=gc_id, supervisor=self.supervisor, battery=battery,
                                    msg_latency=msg_latency, price_logic=price_logic, schedule=schedule,
                                    min_alloc_response_threshold=min_alloc_response_threshold, total_runtime=runtime)
            # make a new grid controller and register it with the supervisor
            self.supervisor.register_device(new_gc)
        return connections

    # make a new utility meter and register with supervisor
    def read_utility_meters(self, config, override_args):

        # TODO: Incorporate new scheduling

        connections = []  # a list of tuples of (utm, [connections]) to initialize later once all devices are set.
        for utm in config['devices']['utility_meters']:
            utm_id = utm['device_id']
            msg_latency = utm.get('message_latency', 0)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(utm_id), msg_latency))
            connected_devices = utm.get('connected_devices', None)
            schedule = utm.get('schedule', None)
            price_schedule = utm.get('price_schedule', None)
            if connected_devices:
                connections.append((utm_id, connected_devices))

            new_utm = UtilityMeter(device_id=utm_id, supervisor=self.supervisor,
                                   msg_latency=msg_latency, schedule=schedule, price_schedule=price_schedule)
            self.supervisor.register_device(new_utm)
        return connections

    def read_pv_data(self, filename):
        data_out = []  # list of tuples of time and power ratios
        pv_data = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                               "scenario_data/pv_data/{}".format(filename))
        with open(pv_data, 'r') as data:
            for raw_line in data:
                for line in raw_line.split("\r"):
                    parts = line.strip().split(',')
                    if len(parts) == 2 and parts[0].strip():
                        time_parts = parts[0].split(':')
                        if len(time_parts) == 3:
                            time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
                            power_ratio = float(parts[1])
                            data_out.append((time_secs, power_ratio))
        return data_out

    def read_pvs(self, config, override_args):
        connections = []
        for pv in config['devices']['pv']:
            pv_id = pv['device_id']
            msg_latency = pv.get('message_latency', 0)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(pv_id), msg_latency))
            connected_devices = pv.get('connected_devices', None)
            schedule = pv.get('schedule', None)
            #output_schedule = pv.get('price_schedule', None)
            # open the file called raw_data.csv.
            if connected_devices:
                connections.append((pv_id, connected_devices))

        pass
        # TODO: Once we implement PV etc.

    def read_euds(self, config, override_args):
        connections = []
        for eud in config['devices']['euds']:
            eud_id = eud['device_id']
            eud_type = eud['eud_type']

            msg_latency = eud.get('message_latency', 0)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(eud_id), msg_latency))
            start_time = eud.get('start_time', 0)
            start_time = int(override_args.get('devices.{}.start_time'.format(eud_id), start_time))
            connected_devices = eud.get('connected_devices', None)
            schedule = eud.get('schedule', None)
            if connected_devices:
                connections.append((eud_id, connected_devices))

            eud_class = self.eud_dictionary[eud_type][0]
            # get all the arguments for the eud constructor
            eud_specific_args = {cls_arg: eud.get(cls_arg, None) for cls_arg in self.eud_dictionary[eud_type][1:]}
            for k, v in eud_specific_args.items():
                eud_specific_args[k] = float(override_args.get('devices.{}.{}'.format(eud_id, k), v))  # TODO: dangerous
            new_eud = eud_class(device_id=eud_id, supervisor=self.supervisor, time=start_time, msg_latency=msg_latency,
                                schedule=schedule, **eud_specific_args)
            self.supervisor.register_device(new_eud)

        return connections

    ##
    # Reads in the simulation json file and any override parameters, creating all the devices which will participate
    # in the simulation.
    #
    # @param config_file the list

    def setup_simulation(self, config_file, override_args):
        self.read_config_file(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                              "scenario_data/{}".format(config_file)))
        self.setup_logging(config_file, override_args)

        overrides = self.parse_inputs_to_dict(override_args)

        run_time_days = self.config["run_time_days"]
        run_time_days = int(overrides.get('run_time_days', run_time_days))
        self.end_time = 24 * 60 * 60 * run_time_days  # end time in seconds

        #  TODO: pv_connections = self.read_pvs(self.config)

        # reads in and creates all the simulation devices before registering them
        connections = [self.read_grid_controllers(self.config, self.end_time, overrides),
                       self.read_utility_meters(self.config, overrides), self.read_euds(self.config, overrides)]

        for connect_list in connections:
            for this_device_id, connects in connect_list:
                this_device = self.supervisor.get_device(this_device_id)
                for that_device_id in connects:
                    that_device = self.supervisor.get_device(that_device_id)
                    this_device.register_device(that_device, that_device_id, 1)
                    that_device.register_device(this_device, this_device_id, 1)

    ##
    # Takes a list of keyword arguments in the form of strings such as 'key=value' and outputs them as
    # a dictionary of string to float values. These inputs must be float override values.

    def parse_inputs_to_dict(self, args):
        arg_dict = {}
        for arg in args:
            key_val = arg.split('=')
            if len(key_val) == 2:
                key, val = key_val
                arg_dict[key] = val
        return arg_dict


##
# Creates an instance of a simulation class, which performs all the necessary file I/O with the input file.
# Then, iterates through all events created in the simulation and writes output to the log file.
# @param config_file the configuration json containing the specifications of the run. See docs for more details.
# @param override_args list of manual parameters to override in the format 'device_id.attribute_name=value'.

def run_simulation(config_file, override_args):

    sim = Simulation()
    sim.supervisor = Supervisor()
    sim.setup_simulation(config_file, override_args)

    while sim.supervisor.has_next_event():
        device_id, time_stamp = sim.supervisor.peek_next_event()
        if time_stamp > sim.end_time:
            break
        sim.supervisor.occur_next_event()

    sim.supervisor.finish_all(sim.end_time)





