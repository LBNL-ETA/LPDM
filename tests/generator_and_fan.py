from tug_devices.grid_controller import GridController
from tug_devices.eud import Eud
from tug_devices.fan_eud import PWMfan_eud
from tug_devices.diesel_generator import DieselGenerator
from messenger import Messenger
from tug_logger import TugLogger

def description():
    return {
        "name": "Test with diesel generator and light"
    }

def run(output_json=True):
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
    }

    gc = GridController(config_grid)
    my_messenger.subscribeToTimeChanges(gc)
    my_messenger.subscribeToPowerChanges(gc)
    my_messenger.subscribeToPriceChanges(gc)

    # setup an EUD - fan
    fan_config = {
        "tug_logger": tlog,
        "uuid": 3,
        "device_name": "EUD - fan",
        "max_power_use": 15000.0,
        "broadcastNewPower": my_messenger.onPowerChange,
        "broadcastNewTTIE": my_messenger.onNewTTIE,
         "schedule": [['0300', 1], ['2300', 0]]  # turn on at 3 AM and off at 11 PM every day
    }

    # fan = Eud(fan_config)
    fan = PWMfan_eud(fan_config)
    my_messenger.subscribeToPriceChanges(fan)
    my_messenger.subscribeToPowerChanges(fan)
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
        "broadcastNewPower": my_messenger.onPowerChange,
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
    max_time = 24 * 60 * 60 * 14
    for time_in_seconds in range(1, max_time):
        # if time_in_seconds == 60:
        #     fan.forceOn(time_in_seconds)
        my_messenger.changeTime(time_in_seconds)
     
    # tlog.dump()
    if output_json:
        return tlog.jsonByMessageType(max_time)
    else:
        return tlog.dump()

# tlog.dumpDevice(light)

# tlog.dumpDevice(gc)

if __name__ == '__main__':
    print(run(output_json=False))

