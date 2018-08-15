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


"""Simulation class for scenario data file IO and setting up the simulation, and functionality to run it."""

import json
import logging
import os
import importlib

from Build.Objects.air_conditioner import AirConditionerSimple
from Build.Objects.battery import Battery
from Build.Objects.fixed_consumption import FixedConsumption
from Build.Objects.load_profile_eud import LoadProfile
from Build.Objects.grid_controller import GridController
from Build.Objects.light import Light
from Build.Objects.pv import PV
from Build.Objects.converter.converter import Converter
from Build.Objects.wire import Wire
from Build.Objects.utility_meter import UtilityMeter
from Build.Simulation_Operation.logger import SimulationLogger
from Build.Simulation_Operation.supervisor import Supervisor
from Build.Simulation_Operation.support import SECONDS_IN_DAY


class SimulationSetup:

    DEFAULT_MESSAGE_LATENCY = 1   # If not specified devices will have a 1 second message processing delay
    DEFAULT_MULTIDAY = 1  # If not specified, all schedules will repeat on a daily basis

    ##
    # Create an instance of the Simulation Setup class, which will contain the supervisor who will orchestrate
    # the simulation
    # @param supervisor the supervisor for this simulation
    def __init__(self, supervisor):
        self.end_time = 0  # time until which to run simulation. Update this in setup_simulation.
        self.supervisor = supervisor   # Supervisor class orchestrating the simulation.
        # A dictionary of eud class names and their respective constructor input names to read from the JSON file
        self.eud_dictionary = {
            'light': [Light, 'max_operating_power', 'power_level_max', 'power_level_low', 'price_dim_start',
                      'price_dim_end', 'price_off'],
            'air_conditioner': [AirConditionerSimple, 'compressor_operating_power', 'initial_temp', 'temp_max_delta',
                                'initial_set_point', 'price_to_setpoint', 'temperature_schedule',
                                'precooling_price_threshold', 'compressor_cooling_rate', 'heat_exchange_rate'],
            'fixed_consumption': [FixedConsumption, 'desired_power_level'],
            'load_profile_eud': [LoadProfile, 'data_filename']
        }

    ##
    # Reads in the configuration JSON and returns the dictionary parsed from it
    # @return a parsed key-value dictionary from the json
    def read_config_file(self, filename):
        with open(filename, 'r') as config_file:
            return json.load(config_file)

    ##
    # Sets up the logging for the simulation by
    # @param config_filename the name of the input JSON file to be included in the header of the log
    # @param config the input parameter dictionary containing info on log levels
    # @param override_args the dictionary of override arguments to include in log header

    def setup_logging(self, config_filename, config, override_args):
        log_manager = SimulationLogger(
            console_log_level=config.get("console_log_level", logging.INFO),  # Default to less info at console
            file_log_level=config.get("file_log_level", logging.DEBUG),
            database_log_level=config.get("database_log_level", logging.DEBUG),
            log_to_database=config.get("log_to_database", False),
        )
        log_manager.initialize_logging(config_filename, override_args)

    #  ________________________JSON READ-IN/DEVICE-INITIALIZATION FUNCTIONS ____________________________________________

    """ Below are a collection of read-in functions, which parse their respective portions of the JSON and create 
    instances of their respective classes, report those devices to the simulation supervisor, 
    and record all the connections between devices which will then be initiated after all the devices are created. 
    """

    ##
    # Reads in information from the parameter dictionary, makes all specified grid controllers and registers them with
    # the supervisor, recording each of their connections
    # @param config the configuration dictionary derived from the input JSON file
    # @param runtime duration of the simulation (used by grid controllers for internal scheduling).
    # @param override_args a dictionary of override arguments
    # @return list of tuples of GC_id's, list of that device's connected devices.

    def make_grid_controllers(self, config, runtime, override_args):

        connections = []  # a list of tuples of (gc, [connections]) to initialize later once all devices are set.
        if 'grid_controllers' not in config['devices']:
            return connections

        for gc in config['devices']['grid_controllers']:
            gc_id = gc['device_id']
            price_logic = gc['price_logic']
            price_logic = override_args.get('devices.{}.price_logic'.format(gc_id), price_logic)

            msg_latency = gc.get('message_latency', self.DEFAULT_MESSAGE_LATENCY)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(gc_id), msg_latency))

            min_alloc_response_threshold = gc.get('threshold_alloc', 1.0)
            min_alloc_response_threshold = float(override_args.get('devices.{}.threshold_alloc'.format(gc_id),
                                                                   min_alloc_response_threshold))

            price_announce_threshold = gc.get('price_announce_threshold', .01)
            price_announce_threshold = float(override_args.get('devices.{}.price_announce_threshold'.format(gc_id),
                                                               price_announce_threshold))

            schedule = gc.get('schedule', None)
            multiday = schedule.get('multiday', self.DEFAULT_MULTIDAY) if schedule else 0
            schedule_items = schedule.get('items', None) if schedule else None

            connected_devices = gc.get('connected_devices', None)
            if connected_devices:
                connections.append((gc_id, connected_devices))

            batt_info = gc.get('battery', None)
            if batt_info:
                battery = self.make_battery(battery_info=batt_info, gc_id=gc_id, override_args=override_args)
            else:
                battery = None
            new_gc = GridController(device_id=gc_id, supervisor=self.supervisor, battery=battery,
                                    msg_latency=msg_latency, price_logic=price_logic, schedule=schedule_items,
                                    min_alloc_response_threshold=min_alloc_response_threshold,
                                    price_announce_threshold=price_announce_threshold, total_runtime=runtime)
            # make a new grid controller and register it with the supervisor
            self.supervisor.register_device(new_gc)
        return connections

    ##
    # Reads in the JSON information about a battery and creates a battery class.
    # @param battery_info a dictionary of parameter-value information about a battery retrieved from the
    # input JSON file.
    # @param gc_id the id of the grid controller to associate this battery with
    # @param override_args a dictionary of override arguments
    # @return the newly created battery

    def make_battery(self, battery_info, gc_id, override_args):

        DEFAULT_MAX_CHARGE_RATE = 1000.0  # 1000W default
        DEFAULT_MAX_DISCHARGE_RATE = 1000.0  # 1000W default
        DEFAULT_UPDATE_RATE = 300  # Update every 5 minutes by default
        DEFAULT_CAPACITY = 10000.0  # Default battery capacity 10000 WH. (10 kWh)
        DEFAULT_STARTING_SOC = 0.5  # Default battery starts at 50% charge

        batt_price_logic = battery_info['price_logic']
        batt_id = battery_info['battery_id']
        max_discharge_rate = battery_info.get('max_discharge_rate', DEFAULT_MAX_DISCHARGE_RATE)
        max_discharge_rate = float(override_args.get('devices.{}.{}.max_discharge_rate'.format(gc_id, batt_id),
                                                     max_discharge_rate))
        max_charge_rate = battery_info.get('max_charge_rate', DEFAULT_MAX_CHARGE_RATE)
        max_charge_rate = float(override_args.get('devices.{}.{}.max_charge_rate'.format(gc_id, batt_id),
                                                  max_charge_rate))
        capacity = battery_info.get('capacity', DEFAULT_CAPACITY)
        capacity = float(override_args.get('devices.{}.{}.capacity'.format(gc_id, batt_id), capacity))
        starting_soc = battery_info.get('starting soc', DEFAULT_STARTING_SOC)
        starting_soc = float(override_args.get('devices.{}.{}.starting_soc'.format(gc_id, batt_id),
                                               starting_soc))
        update_frequency = battery_info.get('update_frequency', DEFAULT_UPDATE_RATE)
        battery = Battery(battery_id=batt_id, price_logic=batt_price_logic, capacity=capacity,
                          max_charge_rate=max_charge_rate, max_discharge_rate=max_discharge_rate,
                          starting_soc=starting_soc, update_frequency=update_frequency)
        return battery

    ##
    # Reads in information from the parameter dictionary, makes all specified utility meters and registers them with
    # the supervisor, recording each of their connections
    # @param config the configuration dictionary derived from the input JSON file
    # @param override_args a dictionary of override arguments
    # @param runtime the duration of the simulation (in seconds)

    def make_utility_meters(self, config, runtime, override_args):
        connections = []  # a list of tuples of (utm, [connections]) to initialize later once all devices are set.
        if 'utility_meters' not in config['devices']:
            return connections
        for utm in config['devices']['utility_meters']:
            utm_id = utm['device_id']
            msg_latency = utm.get('message_latency', self.DEFAULT_MESSAGE_LATENCY)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(utm_id), msg_latency))
            connected_devices = utm.get('connected_devices', None)
            schedule = utm.get('schedule', None)
            multiday = schedule.get('multiday', 0) if schedule else 0
            schedule_items = schedule.get('items', None) if schedule else None

            sell_price_schedule = utm.get('sell_price_schedule', None)
            sell_price_multiday = sell_price_schedule.get('multiday', self.DEFAULT_MULTIDAY) if sell_price_schedule else 0
            sell_price_schedule_items = sell_price_schedule.get('items', None) if sell_price_schedule else None

            buy_price_schedule = utm.get('buy_price_schedule', None)
            buy_price_multiday = buy_price_schedule.get('multiday', self.DEFAULT_MULTIDAY) if buy_price_schedule else 0
            buy_price_schedule_items = buy_price_schedule.get('items', None) if buy_price_schedule else None

            if connected_devices:
                connections.append((utm_id, connected_devices))

            new_utm = UtilityMeter(device_id=utm_id, supervisor=self.supervisor,
                                   msg_latency=msg_latency, schedule=schedule_items, runtime=runtime,
                                   multiday=multiday, sell_price_schedule=sell_price_schedule_items,
                                   sell_price_multiday=sell_price_multiday, buy_price_schedule=buy_price_schedule_items,
                                   buy_price_multiday=buy_price_multiday)
            self.supervisor.register_device(new_utm)
        return connections

    ##
    # Reads in the PV csv data containing information about the proportion of power used at different times during
    # the simulation. Can use PV Watts input
    # @param filename the input filename containing a list of times and associated percentages of peak power
    # @return a list of tuples of time (seconds), and power produced (watts).

    def read_pv_data(self, filename):
        data_out = []  # list of tuples of time and power ratios
        pv_data = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                               "scenario_data/pv_data/{}".format(filename))
        with open(pv_data, 'r') as data:
            # parsing settings depend on whether PVWatts or LPDM data
            if filename == "pvwatts_hourly.csv":
                # Parse data from a PV Watts hourly data format
                DATASTART = 18
                DCPOWERIND = 9
                TIMEPARSE = False
                POWERSCALAR = 1
                for i, line in enumerate(data):
                    # Find the kW solar capacity of the PVWatts data
                    if i == 6:
                        parts = line.strip().split(',')
                        POWERSCALAR = float(parts[1])*1000
                        break
            else:
                # Parse data from LPDM power ratio format
                DATASTART = 0
                DCPOWERIND = 1
                TIMEPARSE = True
                POWERSCALAR = 1
            # Go through each line in CSV and parse power and time data 
            data.seek(0)
            for i, line in enumerate(data):
                if i < DATASTART:
                    continue
                parts = line.strip().split(',')
                if len(parts) >= DCPOWERIND + 1 and parts[0].strip():
                    time_parts = parts[0].split(':')
                    if TIMEPARSE and len(time_parts) == 3:
                        # For LPDM format, Parse time from H:M:S format
                        time_secs = (int(time_parts[0]) * 60 * 60) + (int(time_parts[1]) * 60) + int(time_parts[2])
                    else:
                        # For PVWatts format, get time from row index in hourly increments
                        time_secs = (i - DATASTART)*3600
                    power_ratio = float(parts[DCPOWERIND])/POWERSCALAR
                    data_out.append((time_secs, power_ratio))
        return data_out

    ##
    # Reads in information from the parameter dictionary, makes all specified PV's and registers them with
    # the supervisor, recording each of their connections
    # @param config the configuration input dictionary derived from the JSON parameter file
    # @param runtime the duration of the simulation, in seconds (necessary for PV's internal scheduling)
    # @param override_args dictionary of override arguments
    # @return list of tuples of PV_id's, list of that device's connected devices.

    def make_pvs(self, config, runtime, override_args):
        connections = []
        if 'pvs' not in config['devices']:
            return connections
        for pv in config['devices']['pvs']:
            pv_id = pv['device_id']
            msg_latency = pv.get('message_latency', self.DEFAULT_MESSAGE_LATENCY)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(pv_id), msg_latency))
            connected_devices = pv.get('connected_devices', None)
            input_file = pv['data_filename']
            peak_power = pv['peak_power']
            output_schedule = self.read_pv_data(input_file)
            if connected_devices:
                connections.append((pv_id, connected_devices))

            new_pv = PV(device_id=pv_id, supervisor=self.supervisor, power_profile=output_schedule,
                        peak_power=peak_power, total_runtime=runtime, msg_latency=msg_latency)
            self.supervisor.register_device(new_pv)
        return connections

    ##
    # Reads in the air conditioner temperature data
    # @param filename the name of the input CSV file, containing times and associated temperatures
    # @return a list of tuples of time(seconds) and temperature (celcius).

    def read_air_conditioner_data(self, filename):
        data_out = []  # list of tuples of time and temperature values
        ac_data = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                               "scenario_data/air_conditioner_data/{}".format(filename))
        with open(ac_data, 'r') as data:
            for line in data:
                parts = line.strip().split(',')
                if len(parts) == 2 and parts[0].strip():
                    time_secs = int(float(parts[0]))
                    temp = float(parts[1].strip())
                    data_out.append((time_secs, temp))
        return data_out

    ##
    # Reads in all the information from the JSON about all listed EUD's and creates their connections.
    # Since each EUD might have a different construction signature, this function references the "Eud Dictionary"
    # which has a list of the names of different unique construction parameters for each EUD, and then tries to find
    # the values for those parameters in the configuration file
    # @param config the configuration input dictionary derived from the JSON parameter file
    # @param runtime the duration of the simulation (in seconds)
    # @param override_args the dictionary of override arguments
    # @return list of tuples of EUD_id's, list of that device's connected devices.

    def make_euds(self, config, runtime, override_args):
        connections = []
        if 'euds' not in config['devices']:
            return connections
        for eud in config['devices']['euds']:
            eud_id = eud['device_id']
            eud_type = eud['eud_type']

            msg_latency = eud.get('message_latency', self.DEFAULT_MESSAGE_LATENCY)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(eud_id), msg_latency))
            start_time = eud.get('start_time', 0)
            start_time = int(override_args.get('devices.{}.start_time'.format(eud_id), start_time))
            modulation_interval = eud.get('modulation_interval', 0)  # Default to 0 = do not use modulation.
            modulation_interval = int(override_args.get('devices.{}.modulation_interval'.format(eud_id),
                                                        modulation_interval))
            connected_devices = eud.get('connected_devices', None)
            schedule = eud.get('schedule', None)
            multiday = schedule.get('multiday', self.DEFAULT_MULTIDAY) if schedule else 0
            schedule_items = schedule.get('items', None) if schedule else None

            if connected_devices:
                connections.append((eud_id, connected_devices))

            eud_class = self.eud_dictionary[eud_type][0]
            # get all the arguments for the eud constructor.
            eud_specific_args = {}
            for cls_arg in self.eud_dictionary[eud_type][1:]:
                if cls_arg in eud:
                    eud_specific_args[cls_arg] = eud[cls_arg]

            # look for override values
            for param in eud_specific_args.keys():
                try:
                    eud_specific_args[param] = float(override_args['devices.{}.{}'.format(eud_id, param)])
                except (ValueError, TypeError, KeyError):
                    # Either not a correct float override value or override_args does not contain the value.
                    continue

            external_data = eud.get('external_data', None)
            if external_data:  # external data is a dictionary of constructor names to dictionaries of source info
                for argument, source_info in external_data.items():
                    if source_info:
                        readin_function = source_info['readin_function']
                        source_file = source_info['source_file']
                        func = getattr(self, readin_function)
                        data = func(source_file)
                        eud_specific_args[argument] = data

            new_eud = eud_class(device_id=eud_id, supervisor=self.supervisor, time=start_time, msg_latency=msg_latency,
                                total_runtime=runtime, modulation_interval=modulation_interval,
                                schedule=schedule_items, multiday=multiday, **eud_specific_args)
            self.supervisor.register_device(new_eud)

        return connections
    
    def make_converters(self, config, runtime, override_args):
        "Make the converter objects"
        if "converters" not in config["devices"]:
            return []
        connections = []
        for cv_config in config["devices"]["converters"]:
            device_id = cv_config.get('device_id')
            msg_latency = cv_config.get('message_latency', self.DEFAULT_MESSAGE_LATENCY)
            msg_latency = int(override_args.get('devices.{}.message_latency'.format(device_id), msg_latency))
            start_time = cv_config.get('start_time', 0)
            start_time = int(override_args.get('devices.{}.start_time'.format(device_id), start_time))
            device_input = cv_config.get('device_input', None)
            device_output = cv_config.get('device_output', None)
            # make sure device_input and device_output are both defined
            if not device_input or not device_output:
                raise Exception("Converter {} requires both device_input and device_output to be defined")
            capacity = cv_config.get('capacity')
            # create a list of all connected devices (in + out)
            connections.append((device_id, [device_input, device_output]))

            efficiency_curve = cv_config.get('efficiency_curve', None)

            converter = Converter(
                device_id=device_id,
                supervisor=self.supervisor,
                time=start_time,
                msg_latency=msg_latency,
                device_input=device_input,
                device_output=device_output,
                efficiency_curve=efficiency_curve,
                capacity=capacity
            )
            self.supervisor.register_device(converter)
        return connections

    ##
    # Reads in the simulation json file and any override parameters, creating all the devices which will participate
    # in the simulation and then registering all connected devices with each other.
    # @param config_file the name of the input JSON file (will be parsed in this function)
    # @param override_args_list the list of unparsed override arguments passed into simulation arguments (of format
    # 'device_X.parameter_Y=Z'

    def setup_simulation(self, config_file, override_args_list):
        # Read in the JSON and turn it into a dictionary.
        param_dict = self.read_config_file(os.path.join(
                          os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                          "scenario_data/configuration_files/{}".format(config_file)))

        self.setup_logging(config_filename=config_file, config=param_dict, override_args=override_args_list)


        # Transform the override list into a dictionary of override key, value dictionary
        overrides = self.parse_inputs_to_dict(override_args_list)

        run_time_days = param_dict['run_time_days']
        run_time_days = int(overrides.get('run_time_days', run_time_days))
        self.end_time = SECONDS_IN_DAY * run_time_days
        logging.getLogger("lpdm").info("Total Run Time (s): {}".format(self.end_time))

        if 'devices' not in param_dict:
            raise ValueError("Tried to run a simulation with no devices!")

        # Makes a list of all device's connections before registering them
        connections = [self.make_grid_controllers(config=param_dict, runtime=self.end_time, override_args=overrides),
                       self.make_utility_meters(config=param_dict, runtime=self.end_time, override_args=overrides),
                       self.make_pvs(config=param_dict, runtime=self.end_time, override_args=overrides),
                       self.make_euds(config=param_dict, runtime=self.end_time, override_args=overrides),
                       self.make_converters(config=param_dict, runtime=self.end_time, override_args=overrides)]

        # connect devices together
        self.connect_devices(connections)
        [d.init() for d in self.supervisor.all_devices()]

    def connect_devices(self, connections):
        # For each connection, register those devices with each other
        for connect_list in connections:
            for this_device_id, connects in connect_list:
                this_device = self.supervisor.get_device(this_device_id)
                for connection_item in connects:
                    if type(connection_item) is str:
                        self.connect_devices_without_wire(this_device_id, this_device, connection_item)
                    elif type(connection_item) is dict:
                        self.connect_devices_with_wire(this_device_id, this_device, connection_item)
    
    def connect_devices_without_wire(self, device_id_a, device_a, device_id_b):
        # connect 2 devices together without any wire information
        device_b = self.supervisor.get_device(device_id_b)
        device_a.register_device(device_b, device_id_b, 1)
        device_b.register_device(device_a, device_id_a, 1)
        print("registered no wire {} -> {}".format(device_id_b, device_id_a))
    
    def connect_devices_with_wire(self, device_id_a, device_a, connection_info):
        # connect 2 devices together without any wire information
        device_id = connection_info["device_id"]
        voltage = connection_info["voltage"]
        #wire_class = connection_info["wire_class"]
        resistance = connection_info.get("resistance", None)
        length = connection_info.get("length", 0)
        gauge = connection_info.get("gauge", '14')
        current_type = connection_info.get("current_type", 'DC')
        # load the module
        m = importlib.import_module("Build.Objects.wire")
        # get the class, will raise AttributeError if class cannot be found
        #WireClass = getattr(m, wire_class)
        # build the wire object
        #wire = WireClass(length_m, voltage)
        wire = Wire(voltage, resistance, length, gauge, current_type)

        device_b = self.supervisor.get_device(device_id)
        device_a.register_device(device_b, device_id, 1, wire)
        device_b.register_device(device_a, device_id_a, 1, wire)
        print("registered with wire {} -> {}".format(device_id, device_id_a))

    ##
    # Takes a list of keyword arguments in the form of strings such as 'key=value' and outputs them as
    # a dictionary of string to string values. Ignores whitespace.
    # @param args the list of keyword inputs to separate into a dictionary

    def parse_inputs_to_dict(self, args):
        arg_dict = {}
        for arg in args:
            key_value = arg.split('=')
            if len(key_value) == 2:
                key_val_no_space = map(str.strip, key_value)  # ignore whitespace
                key, val = key_val_no_space
                arg_dict[key] = val
        return arg_dict


##
# Creates an instance of a simulation class, which performs all the necessary file I/O with the input file.
# Then, iterates through all events created in the simulation and writes output to the log file.
# @param config_file the configuration json containing the specifications of the run. See docs for more details.
# @param override_args list of manual parameters to override in the format 'device_id.attribute_name=value'.

def run_simulation(config_file, override_args):

    sim = SimulationSetup(supervisor=Supervisor())
    sim.setup_simulation(config_file, override_args)

    while sim.supervisor.has_next_event():
        device_id, time_stamp = sim.supervisor.peek_next_event()
        if time_stamp > sim.end_time:
            # Reached end of simulation. Stop processing events
            break
        sim.supervisor.occur_next_event()

    sim.supervisor.finish_all(sim.end_time)





