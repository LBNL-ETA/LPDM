from tug_devices.grid_controller import GridController
from tug_devices.eud import Eud
from tug_devices.light import Light
from tug_devices.insight_eud import InsightEud
from tug_devices.diesel_generator import DieselGenerator
from tug_devices.fan_eud import PWMfan_eud
from tug_devices.air_conditioner import AirConditioner
from messenger import Messenger
from tug_logger import TugLogger
from simulation_logger import SimulationLogger
import logging
import os
import re
import pprint
import random
import json
import urllib2

class TugSimulation:
    def __init__(self, params=None):
        # self.logger = logging.getLogger('{}.{}'.format(logger_setup.APP_NAME, __name__))
        self.simulation_log_manager = SimulationLogger()
        self.simulation_id = self.simulation_log_manager.log_id
        self.logger = self.simulation_log_manager.logger

        self.eud_devices = []
        self.grid_controller = None
        self.diesel_generator = None
        self.messenger = None
        self.tug_logger = None

        self.current_time = None
        self.end_time = int(params["run_time_days"]) * 60 * 60 * 24 if params and 'run_time_days' in params.keys() and params['run_time_days'] else 60 * 60 * 24 * 7
        self.status_interval = None

        self.server_ip = params["server_ip"] if params and 'server_ip' in params.keys() else  "***REMOVED***"
        self.server_port = params["server_port"] if params and 'server_port' in params.keys() else "***REMOVED***"
        self.client_id = params["client_id"] if params and 'client_id' in params.keys() else None
        self.socket_id = params["socket_id"] if params and 'socket_id' in params.keys() else None

        self.last_dump = None

        self.device_status = []
        self.device_info = []
        self.simulations = []

        self.initializeSimulation(params)

    def initializeSimulation(self, params):
        self.tug_logger = TugLogger()

        self.logger.info('Initialize Simulation {}'.format(self.simulation_id))
        self.logger.info(pprint.pformat(params))
        self.messenger = Messenger({"device_notifications_through_gc": True})

        uuid = 1
        for device_config in params['devices']:
            device_config["simulation_id"] = self.simulation_id
            device_config["uuid"] = uuid
            device_config["app_log_manager"] = self.simulation_log_manager
            device_config["logger"] = self.logger
            device_config["tug_logger"] = self.tug_logger
            device_config["broadcastNewPrice"] = self.messenger.onPriceChange
            device_config["broadcastNewPower"] = self.messenger.onPowerChange
            device_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

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
                    device_config["battery_config"]["tug_logger"] = self.tug_logger
                    device_config["battery_config"]["uuid"] = uuid
                    device_config["battery_config"]["app_log_manager"] = self.simulation_log_manager
                    device_config["battery_config"]["logger"] = self.logger
                    device_config["battery_config"]["tug_logger"] = self.tug_logger

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
            elif device_config["device_type"] == "air_conditioner":
                device = AirConditioner(device_config)

                self.eud_devices.append(device)
                self.messenger.subscribeToPriceChanges(device)
                self.messenger.subscribeToPowerChanges(device)
                self.messenger.subscribeToTimeChanges(device)
                self.device_info.append({'device': 'air_conditioner', 'config': self.configToJSON(device_config)})
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

    # def defaultDieselGenerator(self):
    #     return {
    #         "device_name": "diesel_generator",
    #         "config_time": 10,
    #         "price": 1.0,
    #         "fuel_tank_capacity": 100.0,
    #         "fuel_level": 100.0,
    #         "fuel_reserve": 20.0,
    #         "days_to_refuel": 7,
    #         "kwh_per_gallon": 36.36,
    #         "time_to_reassess_fuel": 21600,
    #         "fuel_price_change_rate": 5,
    #         "capacity": 2000.0,
    #         "gen_eff_zero": 25,
    #         "gen_eff_100": 40,
    #         "price_reassess_time": 60,
    #         "fuel_base_cost": 5
    #     }

    # def defaultEudFan(self):
    #     return {
    #         "device_name": "EUD - fan",
    #         "max_power_use": 15000.0,
    #         "schedule": [['0300', 1], ['2300', 0]]
    #     }

    # def defaultGridController(self):
    #     return {
    #         "device_name": "Grid Controller",
    #         "capacity": 3000.0,
    #         "connected_devices": [],
    #         "check_battery_soc_rate": 60 * 5,
    #         "battery_config": {
    #             "capacity": 5.0,
    #             "min_soc": 0.20,
    #             "max_soc": 0.80,
    #             "max_charge_rate": 1000.0,
    #             "roundtrip_eff": 0.9
    #         }
    #     }

    def signalSimulationStart(self):
        try:
            req = urllib2.Request('http://{0}:{1}/api/simulation_start'.format(self.server_ip, self.server_port))
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps({"client_id": self.client_id, "socket_id": self.socket_id}))
            return True
        except:
            self.logger.exception("Unable to connect to web client for simulation {}".format(self.simulation_id))
            return False

    def signalSimulationEvent(self, data):
        try:
            data["socket_id"] = self.socket_id
            data["client_id"] = self.client_id
            req = urllib2.Request('http://{0}:{1}/api/simulation_event'.format(self.server_ip, self.server_port))
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps(data))
            return True
        except:
            self.logger.exception("Unable to connect to web client for simulation {}".format(self.simulation_id))
            return False

    def signalSimulationEnd(self):
        try:
            req = urllib2.Request('http://{0}:{1}/api/simulation_end'.format(self.server_ip, self.server_port))
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps({"client_id": self.client_id, "socket_id": self.socket_id}))
            return True
        except:
            self.logger.exception("Unable to connect to web client for simulation {}".format(self.simulation_id))
            return False

    def run(self):
        self.logger.info('run simulation for {} days'.format(self.end_time / 60.0 / 60.0 / 24.0))
        if self.signalSimulationStart():
            for self.current_time in range(0, self.end_time):
                self.messenger.changeTime(self.current_time)
                log = self.tug_logger.jsonTime(self.current_time)
                if log and not self.signalSimulationEvent(log):
                    return

            self.signalSimulationEnd()
            self.logger.info("Simulation #{} finished".format(self.simulation_id))
        else:
            self.logger.exception("Unable to connect to web client for simulation {}".format(self.simulation_id))


