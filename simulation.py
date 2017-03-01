

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
import pprint
import random
import json
import logging
from supervisor import Supervisor
from simulation_logger import SimulationLogger
# from device.diesel_generator import DieselGenerator
# from tug_devices.grid_controller import GridController
# from tug_devices.eud import Eud
# from tug_devices.light import Light
# from tug_devices.insight_eud import InsightEud
# from tug_devices.diesel_generator import DieselGenerator
# from tug_devices.fan_eud import PWMfan_eud
# from tug_devices.refrigerator import Refrigerator
# from tug_devices.air_conditioner import AirConditioner


class TugSimulation:
    def __init__(self, params):
        # setup the logger
        self.simulation_log_manager = SimulationLogger(
            console_log_level=params.get("console_log_level", logging.DEBUG),
            file_log_level=params.get("file_log_level", logging.DEBUG)
        )
        self.simulation_log_manager.init()

        self.simulation_id = self.simulation_log_manager.log_id
        self.logger = self.simulation_log_manager.logger

        self.eud_devices = []
        self.grid_controller = None
        self.diesel_generator = None
        self.messenger = None
        self.temperature_controller = None

        self.current_time = None

        # setup the run_time for the simulation
        run_time_days = params.get("run_time_days", 7)
        self.end_time = run_time_days * 60 * 60 * 24

        # force the devices to ignore changes in price
        self.static_price = params.get("static_price", False)

        self.device_info = []

    def init(self, config):
        """Initialize the devices"""

    def initializeSimulation(self, params):

        self.logger.info('Initialize Simulation {}'.format(self.simulation_id))
        self.logger.info(pprint.pformat(params))
        self.messenger = Messenger({"device_notifications_through_gc": True})

        uuid = 1
        for device_config in params['devices']:
            device_config["simulation_id"] = self.simulation_id
            device_config["uuid"] = uuid
            device_config["app_log_manager"] = self.simulation_log_manager
            device_config["logger"] = self.logger
            device_config["broadcastNewPrice"] = self.messenger.onPriceChange
            device_config["broadcastNewPower"] = self.messenger.onPowerChange
            device_config["broadcastNewTTIE"] = self.messenger.onNewTTIE
            device_config["headless"] = self.headless
            device_config["static_price"] = self.static_price

            if self.headless:
                device_config["dashboard"] = None
            else:
                device_config["dashboard"] = {
                    "host": self.server_ip,
                    "port": self.server_port,
                    "client_id": self.client_id,
                    "socket_id": self.socket_id
                }

            self.logger.info("initialize a {}".format(device_config["device_type"]))

            if device_config["device_type"] == "diesel_generator":
                self.diesel_generator = DieselGenerator(device_config)
                self.messenger.subscribeToPowerChanges(self.diesel_generator)
                self.messenger.subscribeToTimeChanges(self.diesel_generator)

                self.device_info.append({'device': 'diesel_generator', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "grid_controller":
                battery = filter(lambda x: x["device_type"] == "battery", params["devices"])
                if len(battery):
                    device_config['battery_config'] = battery[0]
                    uuid += 1
                    device_config["battery_config"]["uuid"] = uuid
                    device_config["battery_config"]["app_log_manager"] = self.simulation_log_manager
                    device_config["battery_config"]["logger"] = self.logger

                if "pv" in device_config.keys() and device_config["pv"] == "1":
                    uuid += 1
                    device_config["pv_config"] = {}
                    device_config["pv_config"]["uuid"] = uuid
                    device_config["pv_config"]["app_log_manager"] = self.simulation_log_manager
                    device_config["pv_config"]["logger"] = self.logger
                else:
                    device_config["pv_config"] = None

                self.grid_controller = GridController(device_config)
                self.messenger.subscribeToTimeChanges(self.grid_controller)
                self.messenger.subscribeToPowerChanges(self.grid_controller)
                self.messenger.subscribeToPriceChanges(self.grid_controller)

                self.device_info.append({'device': 'grid_controller', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "pwm_fan":
                if "is_real_device" in device_config.keys() and device_config['is_real_device'].strip() == "1":
                    fan = PWMfan_eud(device_config)
                else:
                    fan = Eud(device_config)

                self.eud_devices.append(fan)
                self.messenger.subscribeToPriceChanges(fan)
                self.messenger.subscribeToPowerChanges(fan)
                self.messenger.subscribeToTimeChanges(fan)
                self.device_info.append({'device': 'fan', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "wemo_insight":
                if "is_real_device" in device_config.keys() and device_config['is_real_device'].strip() == "1":
                    wemo_insight = InsightEud(device_config)
                else:
                    wemo_insight = Eud(device_config)

                self.eud_devices.append(wemo_insight)
                self.messenger.subscribeToPriceChanges(wemo_insight)
                self.messenger.subscribeToPowerChanges(wemo_insight)
                self.messenger.subscribeToTimeChanges(wemo_insight)
                self.device_info.append({'device': 'wemo_insight', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "wemo_light":
                if "is_real_device" in device_config.keys() and device_config['is_real_device'].strip() == "1":
                    wemo_light = InsightEud(device_config)
                else:
                    wemo_light = Eud(device_config)

                self.eud_devices.append(wemo_light)
                self.messenger.subscribeToPriceChanges(wemo_light)
                self.messenger.subscribeToPowerChanges(wemo_light)
                self.messenger.subscribeToTimeChanges(wemo_light)
                self.device_info.append({'device': 'wemo_light', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "refrigerator":
                device = Refrigerator(device_config)

                self.eud_devices.append(device)
                self.messenger.subscribeToPriceChanges(device)
                self.messenger.subscribeToPowerChanges(device)
                self.messenger.subscribeToTimeChanges(device)
                self.device_info.append({'device': 'refrigerator', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "air_conditioner":
                device = AirConditioner(device_config)

                self.eud_devices.append(device)
                self.messenger.subscribeToPriceChanges(device)
                self.messenger.subscribeToPowerChanges(device)
                self.messenger.subscribeToTimeChanges(device)
                self.device_info.append({'device': 'air_conditioner', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "eud":
                eud = Eud(device_config)

                self.eud_devices.append(eud)
                self.messenger.subscribeToPriceChanges(eud)
                self.messenger.subscribeToPowerChanges(eud)
                self.messenger.subscribeToTimeChanges(eud)
                self.device_info.append({'device': 'eud', 'config': self.configToJSON(device_config)})

            # elif device_config["device_type"] == "temperature_controller":
                # self.temperature_controller = TemperatureController(device_config)
                # self.messenger.subscribeToTimeChanges(self.temperature_controller)
                # self.device_info.append({'device': 'temperature_controller', 'config': self.configToJSON(device_config)})
            uuid += 1

        self.grid_controller.addDevice(self.diesel_generator.deviceID(), type(self.diesel_generator))
        for eud in self.eud_devices:
            self.grid_controller.addDevice(eud.deviceID(), type(eud))

    def configToJSON(self, config):
        new_dict = {}
        for prop in config.keys():
            if not callable(config[prop]):
                if type(config[prop]) == type({}):
                    new_dict[prop] = self.configToJSON(config[prop])
                elif type(config[prop]) in [type(1), type(1.1), type('')]:
                    new_dict[prop] = config[prop]
        return new_dict

    def finishSimulation(self):
        for dev in self.eud_devices:
            dev.finish()
            dev.generatePlots()

        self.grid_controller.finish()
        self.grid_controller.generatePlots()

        self.diesel_generator.finish()
        self.diesel_generator.generatePlots()


    def run(self):
        supervisor = Supervisor()
        supervisor.add_device("device_1", Device, {"device_id": "device_1"})
        supervisor.add_device("device_2", Device, {"device_id": "device_2"})
        supervisor.run_simulation()

if __name__ == "__main__":
    with open("scenarios/scenario.json") as config_file:
        config = json.load(config_file)
    print config
    # setup logging for the app
    log_manager = SimulationLogger(
        console_log_level=config.get("console_log_level", logging.DEBUG),
        file_log_level=config.get("file_log_level", logging.DEBUG),
        pg_log_level=config.get("pg_log_level", logging.DEBUG)
    )
    log_manager.init()

    supervisor = Supervisor()
    supervisor.load_config(config)

    log_manager.logger.info("run the simulation")
    supervisor.run_simulation()
