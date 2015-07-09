"""
    Run a test on the generator and light.
    Setup a generator and a light that turns on and off at certain periods of the day, 
"""

from messenger import Messenger
from tug_devices.diesel_generator import DieselGenerator
from tug_devices.eud import Eud

my_messenger = Messenger()

light_config = {
    "device_name": "EUD - light",
    "max_power_use": 100.0,
    "broadcastNewPower": my_messenger.onPowerChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE,
    "schedule": [['0800', 1], ['1800', 0]]  # turn on at 8 AM and off at 6 PM every day
}

light = Eud(light_config)
my_messenger.subscribeToPriceChanges(light)
my_messenger.subscribeToTimeChanges(light)

diesel_config = {
    "device_name": "diesel_generator",
    "config_time": 10,
    "uuid": 1,
    "price": 1.0,
    "broadcastNewPrice": my_messenger.onPriceChange,
    "broadcastNewTTIE": my_messenger.onNewTTIE,
    "fuel_tank_capacity": 200.0,
    "fuel_level": 100.0,
    "fuel_reserve": 20.0,
    "days_to_refuel": 7,
    "kwh_per_gallon": 36.36,
    "time_to_reassess_fuel": 21600,
    "fuel_price_change_rate": 5,
    "capacity": 2000,
    "gen_eff_zero": 25,
    "gen_eff_100": 40,
    "price_reassess_time": 60,
    "fuel_base_cost": 5
}

generator = DieselGenerator(diesel_config)
my_messenger.subscribeToPowerChanges(generator)
my_messenger.subscribeToTimeChanges(generator)

for time_in_seconds in range(1, 24 * 60 * 60 * 5):
    my_messenger.changeTime(time_in_seconds)


