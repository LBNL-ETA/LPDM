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
    def __init__(self, params=None):
        self.eud_devices = None
        self.grid_controller = None
        self.diesel_generator = None
        self.messenger = None
        self.logger = None
        self.current_time = None
        self.end_time = None
        self.status_interval = None
        self.app_instance_id = None
        self.sim_config = params

        self.last_dump = None

        self.device_status = []
        self.device_info = []
        self.simulations = []

        print('sim_config')
        print(self.sim_config)

        self.setSimulations()

    def setSimulations(self):
        self.simulations.append({"id": 1, "name": "Generator and PWM-Fan"})
        self.simulations.append({"id": 2, "name": "Generator and Wemo Light"})
        self.simulations.append({"id": 3, "name": "Generator and Wemo Insight"})

    def initializeSimulation(self, params=None):

        self.logger = TugLogger()
        
        self.messenger = Messenger({"device_notifications_through_gc": True})

        # Setup the Grid Controller
        config_grid = self.defaultGridController()
        config_grid["tug_logger"] = self.logger
        config_grid["uuid"] = 1
        config_grid["broadcastNewPower"] = self.messenger.onPowerChange
        config_grid["broadcastNewTTIE"] = self.messenger.onNewTTIE
        config_grid["broadcastNewPrice"] = self.messenger.onPriceChange
        config_grid["battery_config"]["tug_logger"] = self.logger

        self.grid_controller = GridController(config_grid)
        self.messenger.subscribeToTimeChanges(self.grid_controller)
        self.messenger.subscribeToPowerChanges(self.grid_controller)
        self.messenger.subscribeToPriceChanges(self.grid_controller)
        self.device_info.append({'device': 'grid_controller', 'config': self.configToJSON(config_grid)})

        # Setup EUD's
        self.eud_devices = []
        fan_config = self.defaultEudFan()
        for key in params['pwm_fan'].keys():
            fan_config[key] = params['pwm_fan'][key]

        fan_config["tug_logger"] = self.logger
        fan_config["uuid"] = 2
        fan_config["broadcastNewPower"] = self.messenger.onPowerChange
        fan_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

        print('fan')
        print(fan_config)
        if (fan_config['simulated_fan']):
            fan = Eud(fan_config)
        else:
            fan = PWMfan_eud(fan_config)

        self.eud_devices.append(fan)
        self.messenger.subscribeToPriceChanges(fan)
        self.messenger.subscribeToPowerChanges(fan)
        self.messenger.subscribeToTimeChanges(fan)
        self.grid_controller.addDevice(fan.deviceID(), type(fan))
        self.device_info.append({'device': 'fan', 'config': self.configToJSON(fan_config)})

        # if params['wemo_light']:
        #     print("**** wemo light")
        #     wemo_config = self.defaultEudFan()
        #     for key in params['wemo_light'].keys():
        #         wemo_config[key] = params['wemo_light'][key]

        #     wemo_config["tug_logger"] = self.logger
        #     wemo_config["uuid"] = 4
        #     wemo_config["broadcastNewPower"] = self.messenger.onPowerChange
        #     wemo_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

        #     print('wemo light')
        #     print(wemo_config)
        #     wemo_light = Light(wemo_config)

        #     self.eud_devices.append(wemo_light)
        #     self.messenger.subscribeToPriceChanges(wemo_light)
        #     self.messenger.subscribeToPowerChanges(wemo_light)
        #     self.messenger.subscribeToTimeChanges(wemo_light)
        #     self.grid_controller.addDevice(wemo_light.deviceID(), type(wemo_light))
        #     self.device_info.append({'device': 'wemo_light', 'config': self.configToJSON(wemo_config)})

        if params['wemo_insight']:
            print("**** wemo insight")
            insight_config = self.defaultEudFan()
            for key in params['wemo_insight'].keys():
                insight_config[key] = params['wemo_insight'][key]

            insight_config["tug_logger"] = self.logger
            insight_config["uuid"] = 4
            insight_config["broadcastNewPower"] = self.messenger.onPowerChange
            insight_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

            print('wemo insight')
            print(insight_config)
            if (fan_config['simulated_fan']):
                wemo_insight = Eud(insight_config)
            else:
                wemo_insight = InsightEud(insight_config)
            

            self.eud_devices.append(wemo_insight)
            self.messenger.subscribeToPriceChanges(wemo_insight)
            self.messenger.subscribeToPowerChanges(wemo_insight)
            self.messenger.subscribeToTimeChanges(wemo_insight)
            self.grid_controller.addDevice(wemo_insight.deviceID(), type(wemo_insight))
            self.device_info.append({'device': 'wemo_insight', 'config': self.configToJSON(insight_config)})


        # Setup the Diesel Generator
        # diesel_config = self.defaultDieselGenerator()
        print('diesel generator')
        print(params['diesel_generator'])
        diesel_config = self.defaultDieselGenerator()
        for key in params['diesel_generator'].keys():
            diesel_config[key] = params['diesel_generator'][key]

        diesel_config["tug_logger"] = self.logger
        diesel_config["uuid"] = 3
        diesel_config["broadcastNewPrice"] = self.messenger.onPriceChange
        diesel_config["broadcastNewPower"] = self.messenger.onPowerChange
        diesel_config["broadcastNewTTIE"] = self.messenger.onNewTTIE

        self.diesel_generator = DieselGenerator(diesel_config)
        self.messenger.subscribeToPowerChanges(self.diesel_generator)
        self.messenger.subscribeToTimeChanges(self.diesel_generator)
        self.grid_controller.addDevice(self.diesel_generator.deviceID(), type(self.diesel_generator))
        self.device_info.append({'device': 'diesel_generator', 'config': self.configToJSON(diesel_config)})

        self.diesel_generator.calculateElectricityPrice()

        self.current_time = 0
        self.end_time = self.sim_config["end_time"]

        self.status_interval = self.sim_config["poll_interval"]

        self.app_instance_id = random.randint(1, 1000000)

        return self.device_info

    def configToJSON(self, config):
        new_dict = {}
        for prop in config.keys():
            if not callable(config[prop]):
                if type(config[prop]) == type({}):
                    new_dict[prop] = self.configToJSON(config[prop])
                elif type(config[prop]) in [type(1), type(1.1), type('')]:
                    new_dict[prop] = config[prop]
        return new_dict

    def defaultDieselGenerator(self):
        return {
            "device_name": "diesel_generator",
            "config_time": 10,
            "price": 1.0,
            "fuel_tank_capacity": 100.0,
            "fuel_level": 100.0,
            "fuel_reserve": 20.0,
            "days_to_refuel": 7,
            "kwh_per_gallon": 36.36,
            "time_to_reassess_fuel": 21600,
            "fuel_price_change_rate": 5,
            "capacity": 2000.0,
            "gen_eff_zero": 25,
            "gen_eff_100": 40,
            "price_reassess_time": 60,
            "fuel_base_cost": 5
        }

    def defaultEudFan(self):
        return {
            "device_name": "EUD - fan",
            "max_power_use": 15000.0,
            "schedule": [['0300', 1], ['2300', 0]]
        }

    def defaultGridController(self):
        return {
            "device_name": "Grid Controller",
            "capacity": 3000.0,
            "connected_devices": [],
            "check_battery_soc_rate": 60 * 5,
            "battery_config": {
                "capacity": 5.0,
                "min_soc": 0.20,
                "max_soc": 0.80,
                "max_charge_rate": 1000.0,
                "roundtrip_eff": 0.9
            }
        }

    def run(self, step=None):
        if step == None:
            step = self.end_time - self.current_time

        min_time = self.current_time
        max_time = self.current_time + step

        for self.current_time in range(min_time, max_time):
            # if self.current_time == 60 * 60 * 24 * 3:
            #     self.diesel_generator._days_to_refuel = 14
            #     self.diesel_generator.refresh()

            self.messenger.changeTime(self.current_time)

            # if not self.current_time % self.status_interval:
            #     self.logDeviceStatus()

        self.current_time += 1
        return json.dumps(self.getDeviceStatus())

    def __iter__(self):
        return self

    def next(self):
        if self.current_time > self.end_time:
            raise StopIteration

        min_time = self.current_time
        max_time = self.end_time

        for self.current_time in range(min_time, max_time):
            if self.current_time == 60:
                self.eud_devices[0].turnOn()

            self.messenger.changeTime(self.current_time)

            if not self.current_time % self.status_interval:
                break

        print("dump results at {0} with max_time {1}".format(self.current_time, max_time))
        self.current_time += 1
        return json.dumps(self.getDeviceStatus())

    def getDeviceStatus(self):
        current_status = {"time": self.current_time, "devices": []}
        current_status["devices"].append(self.diesel_generator.status())
        for device in self.eud_devices:
            current_status["devices"].append(device.status())
        return current_status

    def logDeviceStatus(self):
        self.device_status.append(self.getDeviceStatus())

    def deviceStatus(self):
        return self.device_status

    def dumpLog(self):
        self.logger.dump()

        