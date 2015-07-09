"""
    Run a simple test for the diesel generator.
    Setup a messenger to call and receive price, power, and time events, then move time along by seconds.
    The diesel log file will show the details of the events it's processing
"""
from messenger import Messenger
from tug_devices.diesel_generator import DieselGenerator

my_messenger = Messenger()

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


for time_in_seconds in range(1, 24 * 60 * 60 * 10):
    # at 3660 seconds change power to 0.5 kW
    if time_in_seconds == 3660:
        my_messenger.changePower(time_in_seconds, 0.5)
    # elif time_in_seconds == 7260:
    #     my_messenger.changePower(time_in_seconds, 300.0)

    my_messenger.changeTime(time_in_seconds)


