from tug_devices.grid_controller import GridController
from tug_devices.eud import Eud
from tug_devices.diesel_generator import DieselGenerator
from messenger import Messenger
from tug_logger import TugLogger

tlog = TugLogger()

# Setup the messenger to pass notifications through to the different devices
config_messenger = {
    "device_notifications_through_gc": True
}
my_messenger = Messenger(config_messenger)

# Setup the Grid Controller
config_grid = {
    "tug_logger": tlog,
    "uuid": 1,
    "device_name": "Grid Controller",
    "capacity": 3000.0,
    "connected_devices": [],
    "broadcastNewPower": my_messenger.onPowerChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE,
    "broadcastNewPrice": my_messenger.onPriceChange,
    "check_battery_soc_rate": 60 * 5,
    "battery_config": {
        "capacity": 5.0,
        "min_soc": 0.20,
        "max_soc": 0.80,
        "max_charge_rate": 1000.0,
        "roundtrip_eff": 0.9
    }
}

gc = GridController(config_grid)
my_messenger.subscribeToTimeChanges(gc)
my_messenger.subscribeToPowerChanges(gc)
my_messenger.subscribeToPriceChanges(gc)

# setup an EUD - light
light_config = {
    "tug_logger": tlog,
    "uuid": 2,
    "device_name": "EUD - light",
    "max_power_use": 100.0,
    "broadcastNewPower": my_messenger.onPowerChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE,
    "schedule": [['0800', 1], ['1800', 0]]  # turn on at 8 AM and off at 6 PM every day
}

light = Eud(light_config)
my_messenger.subscribeToPriceChanges(light)
my_messenger.subscribeToTimeChanges(light)
gc.addDevice(light.deviceID(), type(light))

# setup an EUD - fan
fan_config = {
    "tug_logger": tlog,
    "uuid": 3,
    "device_name": "EUD - fan",
    "max_power_use": 120.0,
    "broadcastNewPower": my_messenger.onPowerChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE
}

fan = Eud(fan_config)
my_messenger.subscribeToPriceChanges(fan)
my_messenger.subscribeToTimeChanges(fan)
gc.addDevice(fan.deviceID(), type(fan))

# setupa diesel generator
diesel_config = {
    "tug_logger": tlog,
    "device_name": "diesel_generator",
    "config_time": 10,
    "uuid": 4,
    "price": 1.0,
    "broadcastNewPrice": my_messenger.onPriceChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE,
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

generator = DieselGenerator(diesel_config)
my_messenger.subscribeToPowerChanges(generator)
my_messenger.subscribeToTimeChanges(generator)
gc.addDevice(generator.deviceID(), type(generator))

# devices have all been setup
# tell the diesel generator to broadcast a new price
# This should trigger call to on price change to the grid controller
generator.calculateElectricityPrice()

for time_in_seconds in range(1, 24 * 60 * 60 * 7):
    if time_in_seconds == 60:
        fan.turnOn(time_in_seconds)

    my_messenger.changeTime(time_in_seconds)
 
tlog.dump()

# tlog.dumpDevice(light)

# tlog.dumpDevice(gc)


