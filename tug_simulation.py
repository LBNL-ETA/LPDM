from tug_devices.grid_controller import GridController
from tug_devices.eud import Eud
from tug_devices.light import Light
from tug_devices.insight_eud import InsightEud
from tug_devices.diesel_generator import DieselGenerator
from tug_devices.fan_eud import PWMfan_eud
from messenger import Messenger
from tug_logger import TugLogger
import random
import json

class TugSimulation:
    def __init__(self, params=None, zerorpc_client=None):
        self.eud_devices = []
        self.grid_controller = None
        self.diesel_generator = None
        self.messenger = None
        self.logger = None

        self.current_time = None
        self.end_time = int(params["run_time_days"]) * 60 * 60 * 24 if params and 'run_time_days' in params.keys() and params['run_time_days'] else 60 * 60 * 24 * 7
        self.status_interval = None

        self.client_id = params["client_id"] if params and 'client_id' in params.keys() else None
        self.socket_id = params["socket_id"] if params and 'socket_id' in params.keys() else None

        self.last_dump = None

        self.device_status = []
        self.device_info = []
        self.simulations = []

        self.zerorpc_client = zerorpc_client
        self.initializeSimulation(params)

    def initializeSimulation(self, params):
        self.logger = TugLogger()
        
        self.messenger = Messenger({"device_notifications_through_gc": True})

        uuid = 1
        for device_config in params['devices']:
            device_config["tug_logger"] = self.logger
            device_config["uuid"] = uuid
            device_config["broadcastNewPrice"] = self.messenger.onPriceChange
            device_config["broadcastNewPower"] = self.messenger.onPowerChange
            device_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

            if device_config["device_type"] == "diesel_generator":
                self.diesel_generator = DieselGenerator(device_config)
                self.messenger.subscribeToPowerChanges(self.diesel_generator)
                self.messenger.subscribeToTimeChanges(self.diesel_generator)
                
                self.device_info.append({'device': 'diesel_generator', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "grid_controller":
                if 'battery_config' not in device_config.keys():
                    device_config['battery_config'] = {}

                device_config["battery_config"]["tug_logger"] = self.logger

                self.grid_controller = GridController(device_config)
                self.messenger.subscribeToTimeChanges(self.grid_controller)
                self.messenger.subscribeToPowerChanges(self.grid_controller)
                self.messenger.subscribeToPriceChanges(self.grid_controller)

                self.device_info.append({'device': 'grid_controller', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "pwm_fan":
                if (device_config['simulated_fan'].strip() == "1"):
                    fan = Eud(device_config)
                else:
                    fan = PWMfan_eud(device_config)

                self.eud_devices.append(fan)
                self.messenger.subscribeToPriceChanges(fan)
                self.messenger.subscribeToPowerChanges(fan)
                self.messenger.subscribeToTimeChanges(fan)
                self.grid_controller.addDevice(fan.deviceID(), type(fan))
                self.device_info.append({'device': 'fan', 'config': self.configToJSON(device_config)})
            elif device_config["device_type"] == "wemo_insight":
                if (device_config['simulated_device'].strip() == "1"):
                    wemo_insight = Eud(device_config)
                else:
                    wemo_insight = InsightEud(device_config)

                self.eud_devices.append(wemo_insight)
                self.messenger.subscribeToPriceChanges(wemo_insight)
                self.messenger.subscribeToPowerChanges(wemo_insight)
                self.messenger.subscribeToTimeChanges(wemo_insight)
                self.grid_controller.addDevice(wemo_insight.deviceID(), type(wemo_insight))
                self.device_info.append({'device': 'wemo_insight', 'config': self.configToJSON(device_config)})

            uuid += 1

        self.grid_controller.addDevice(self.diesel_generator.deviceID(), type(self.diesel_generator))

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
        if self.zerorpc_client:
            try:
                self.zerorpc_client.simulationStart({"socket_id": self.socket_id, "client_id": self.client_id})
                return True
            except:
                print('unable to signal client')
        return False

    def signalSimulationEvent(self, data):
        if self.zerorpc_client:
            try:
                data["socket_id"] = self.socket_id
                data["client_id"] = self.client_id
                self.zerorpc_client.simulationEvent(data)
                return True
            except:
                print('unable to signal client')
        return False

    def signalSimulationEnd(self):
        if self.zerorpc_client:
            try:
                self.zerorpc_client.simulationEnd({"socket_id": self.socket_id, "client_id": self.client_id})
                return True
            except:
                print('unable to signal client')
        return False

    def run(self):
        print('run simulation from {0} to {1}'.format(0, self.end_time))
        if self.signalSimulationStart():
            for self.current_time in range(0, self.end_time):
                self.messenger.changeTime(self.current_time)
                log = self.logger.jsonTime(self.current_time)
                if log:
                    self.signalSimulationEvent(log)
            
            self.signalSimulationEnd()
            print('finished simulation')
        else:
            print('unable to connect to client')

        