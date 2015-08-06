"""
    Implementation of a general EUD device
"""
from device import Device
import logging

class Eud(Device):
    def __init__(self, config = None):
        # set the properties for an end-use device
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "EUD"

        # max power - set default to 100 watts unless different value provided in configuration
        # operate at max_power_use unless price > 'price_dim'
        self._max_power_use = float(config["max_power_use"]) if type(config) is dict and "max_power_use" in config.keys() else 100.0

        # the price (c/kWh) at which to begin dimming down the power
        # when price > 'price_dim', linearly dim down to power level (%) set at 'power_level_low' of power at 'price_off'
        self._price_dim = float(config["price_dim"]) if type(config) is dict and "price_dim" in config.keys() else 0.3

        # the price (c/kWh) at which to turn off the power completeley
        self._price_off = float(config["price_off"]) if type(config) is dict and "price_off" in config.keys() else 0.7

        # the max operating power level (%)
        self._power_level_max = float(config["power_level_max"]) if type(config) is dict and "power_level_max" in config.keys() else 100.0

        # the power level (%) to dim down to when price between price_dim and price_off
        self._power_level_low = float(config["power_level_low"]) if type(config) is dict and "power_level_low" in config.keys() else 20.0

        self._daily_schedule = self.parseSchedule(config["schedule"]) if type(config) is dict and "schedule" in config.keys() else None
        print('schedule')
        print(self._daily_schedule)

        self._power_level = 0.0

        # call the super constructor
        Device.__init__(self, config)

        # set the units
        self._units = 'W'

        # load a set of attribute values if a 'scenario' key is present
        if type(config) is dict and 'scenario' in config.keys():
            self.setScenario(config['scenario'])

        # if self._price > 0:
            # self.setPowerLevel()
            # self.broadcastNewPower(self._power_level)

    def status(self):
        return {
            "type": "eud",
            "name": self._device_name,
            "in_operation": self._in_operation,
            "power_level": self._power_level,
            "fuel_price": self._price
        }

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turnOff()
                self.tugLogAction(action="operation", is_initial_event=True, value=0, description="off")
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        self._time = time
        self._price = new_price
        self.setPowerLevel()

        return

    def onTimeChange(self, new_time):
        "Receives message when a time change has occured"
        # print("time change {0} - {1}".format(self.deviceName(), new_time))
        self._time = new_time
        self.processEvent()
        self.calculateNextTTIE()
        return

    def forceOn(self, time):
        if not self._in_operation:
            self._time = time
            self.turnOn()

    def forceOff(self, time):
        if self._in_operation:
            self._time = time
            self.turnOff()

    def turnOn(self):
        "Turn on the device"
        if not self._in_operation:
            self._in_operation = True
            print('turn on the fan at {0}'.format(self._time))
            self.setPowerLevel()

    def turnOff(self):
        "Turn off the device"
        if self._in_operation:
            self._power_level = 0.0
            self._in_operation = False

    def processEvent(self):
        if (self._next_event and self._time == self._ttie):
            print('process event  {0} at {1}'.format(self._next_event["operation"], self._time))
            if self._in_operation and self._next_event["operation"] == 0:
                self.tugLogAction(action="operation", is_initial_event=True, value=0, description="off")
                self.turnOff()
                self.broadcastNewPower(0.0)
            elif not self._in_operation and self._next_event["operation"] == 1:
                new_power = self.calculateNewPowerLevel()
                self.setPowerLevel()

            self.calculateNextTTIE()
            # print('next ttie at {0}'.format(self._ttie))

    def calculateNextTTIE(self):
        "Override the base class function"
        if type(self._daily_schedule) is list:
            current_time_of_day_seconds = self.timeOfDaySeconds()
            new_ttie = None
            next_event = None
            for item in self._daily_schedule:
                if item['time_of_day_seconds'] > current_time_of_day_seconds:
                    new_ttie = int(self._time / (24 * 60 * 60)) * (24 * 60 * 60) + item['time_of_day_seconds']
                    next_event = item
                    break

            if not new_ttie:
                for item in self._daily_schedule:
                    if item['time_of_day_seconds'] > 0:
                        new_ttie = int(self._time / (24.0 * 60.0 * 60.0)) * (24 * 60 * 60) + (24 * 60 * 60) + item['time_of_day_seconds']
                        next_event = item
                        break

            if new_ttie != self._ttie:
                self._next_event = next_event
                self._ttie = new_ttie
                self.broadcastNewTTIE(new_ttie)

    def parseSchedule(self, schedule):
        if type(schedule) is list:
            return self.loadArraySchedule(schedule)

    def loadArraySchedule(self, schedule):
        if type(schedule) is list:
            parsed_schedule = []
            for (task_time, task_operation) in schedule:
                if len(task_time) != 4 or task_operation not in (0,1):
                    raise Exception("Invalid schedule definition ({0}, {1})".format(task_time, task_operation))
                parsed_schedule.append({"time_of_day_seconds": (int(task_time[0:2]) * 60 * 60 + int(task_time[2:]) * 60), "operation": task_operation})
            return parsed_schedule


    # eud specific methods
    def setPowerLevel(self):
        "Set the power level for the eud (W).  If the energy consumption has changed then broadcast the new power usage."

        new_power = self.calculateNewPowerLevel()

        if new_power != self._power_level:
            self._power_level = new_power
            self.tugLogAction(action="set_power_level", is_initial_event=False, value=self._power_level, description='W')

            if self._power_level == 0 and self._in_operation:
                self.turnOff()
                self.tugLogAction(action="operation", is_initial_event=True, value=0, description="off")
            elif self._power_level > 0 and not self._in_operation:
                self.turnOn()
                self.tugLogAction(action="operation", is_initial_event=True, value=1, description="on")
            else:
                self.adjustHardwarePower()
            
            self.broadcastNewPower(new_power)

    def adjustHardwarePower(self):
        "Override this method to tell the hardware to adjust its power output"
        return None

    def calculateNewPowerLevel(self):
        "Set the power level of the eud"
        if self._price <= self._price_dim:
            return self._max_power_use
        elif self._price <= self._price_off:
            return self.interpolatePower()
        else:
            return 0.0

    def interpolatePower(self):
        "Calculate energy consumption for the eud (in this case a linear interpolation) when the price is between price_dim and price_off."
        power_reduction_ratio = (self._price - self._price_dim) / (self._price_off - self._price_dim)
        power_level_percent = self._power_level_max - (self._power_level_max - self._power_level_low) * power_reduction_ratio
        return self._max_power_use * power_level_percent / 100.0


