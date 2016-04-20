"""
    Implementation of a general EUD device
"""
from device import Device
import colors
import logging

class Eud(Device):
    def __init__(self, config = None):
        if not "_device_type" in dir(self) or not self._device_type:
            self._device_type = "eud"

        # set the properties for an end-use device
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "EUD"

        # max power - set default to 100 watts unless different value provided in configuration
        # operate at max_power_use unless price > 'price_dim'
        self._max_power_use = float(config["max_power_use"]) if type(config) is dict and "max_power_use" in config.keys() else 100.0

        # the price (c/kWh) at which to begin dimming down the power
        # when price > 'price_dim_start' and price < 'price_dim_end', linearly dim down to power level (%) set at 'power_level_low' of power at 'price_dim_end'
        self._price_dim_start = float(config["price_dim_start"]) if type(config) is dict and "price_dim_start" in config.keys() else 0.3

        # the price ($/kWh) at which to stop dimming the power output
        # when price > price_dim_end and price < price_off, set to power_level_low
        self._price_dim_end = float(config["price_dim_end"]) if type(config) is dict and "price_dim_end" in config.keys() else 0.7

        # the price ($/kWh) at which to turn off the power completeley
        self._price_off = float(config["price_off"]) if type(config) is dict and "price_off" in config.keys() else 0.9

        # the max operating power level (%)
        self._power_level_max = float(config["power_level_max"]) if type(config) is dict and "power_level_max" in config.keys() else 100.0

        # the power level (%) to dim down to when price between price_dim and price_off
        # the low operating power level
        self._power_level_low = float(config["power_level_low"]) if type(config) is dict and "power_level_low" in config.keys() else 20.0

        # _schedule_array is the raw schedule passed in
        # _dailY_schedule is the parsed schedule used by the device to schedule events
        self._schedule_array = config["schedule"] if type(config) is dict and config.has_key("schedule") else None
        self._daily_schedule = self.parseSchedule(self._schedule_array) if self._schedule_array else None

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

    def getLogMessageString(self, message):
        return colors.colorize(Device.getLogMessageString(self, message), colors.Colors.GREY)

    def status(self):
        return {
            "type": "eud",
            "name": self._device_name,
            "in_operation": self._in_operation,
            "power_level": self._power_level,
            "fuel_price": self._price
        }

    def refresh(self):
        "Refresh the eud. For a basic eud this means resetting the operation schedule."
        self._ttie = None
        self._next_event = None
        self._events = []
        self._daily_schedule = self.parseSchedule(self._schedule_array) if self._schedule_array else None

        # turn on/off the device based on the updated schedule
        should_be_in_operation = self.should_be_in_operation()

        if should_be_in_operation and not self._in_operation:
            self.turnOn()
        elif not should_be_in_operation and self._in_operation:
            self.turnOff()

        self.calculateNextTTIE()

    def should_be_in_operation(self):
        """determine if the device should be operating when a refresh event occurs"""

        current_time_of_day_seconds = self.timeOfDaySeconds()
        operating = False
        for item in self._daily_schedule:
            if  item['time_of_day_seconds'] > current_time_of_day_seconds:
                break
            else:
                operating = True if item['operation'] == 1 else False
        return operating

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        if target_device_id == self._device_id:
            if new_power == 0 and self._in_operation:
                self._time = time
                self.turnOff()
        return

    def current_schedule_value(self):
        current_time_of_day_seconds = self.timeOfDaySeconds()
        res = None
        for schedule_pt in self._daily_schedule:
            if schedule_pt["time_of_day_seconds"] <= current_time_of_day_seconds:
                res = schedule_pt["operation"]
        if not res:
            res = self._daily_schedule[-1]["operation"]
        return res

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self._time = time
            self._price = new_price
            self.logMessage("received new price {}".format(new_price))
            if self.current_schedule_value():
                self.setPowerLevel()
            return

    # def onPriceChange(self, source_device_id, target_device_id, time, new_price):
    #     "Receives message when a price change has occured"
    #     self._time = time
    #     self._price = new_price
    #     self.setPowerLevel()

    #     return

    def onTimeChange(self, new_time):
        "Receives message when a time change has occured"
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
            self.tugSendMessage(action="operation", is_initial_event=True, value=1, description="on")
            self.logMessage("Turn on eud {}".format(self._device_name))
            self.setPowerLevel()

    def turnOff(self):
        "Turn off the device"

        if self._in_operation:
            self._power_level = 0.0
            self._in_operation = False
            self.tugSendMessage(action="operation", is_initial_event=True, value=0, description="off")
            self.logMessage("Turn off eud {}".format(self._device_name))

    def processEvent(self):
        if (self._next_event and self._time == self._ttie):
            if self._in_operation and self._next_event["operation"] == 0:
                self.turnOff()
                self.broadcastNewPower(0.0)
            elif not self._in_operation and self._next_event["operation"] == 1:
                self.setPowerLevel()

            self.calculateNextTTIE()

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
                task_operation = int(task_operation)
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
            self.tugSendMessage(action="set_power_level", is_initial_event=False, value=self._power_level, description='W')

            if self._power_level == 0 and self._in_operation:
                self.turnOff()

            elif self._power_level > 0 and not self._in_operation:
                self.turnOn()
            else:
                self.adjustHardwarePower()

            self.broadcastNewPower(new_power)

    def adjustHardwarePower(self):
        "Override this method to tell the hardware to adjust its power output"
        return None

    def calculateNewPowerLevel(self):
        "Set the power level of the eud"
        if self._static_price:
            return self._max_power_use
        else:
            if self._price <= self._price_dim_start:
                return self._max_power_use
            elif self._price <= self._price_dim_end:
                return self.interpolatePower()
            elif self._price <= self._price_off:
                return self.getPowerLevelLow()
            else:
                return 0.0

    def getPowerLevelLow(self):
        """calculate the lowest operating power output"""
        return self._max_power_use * (self._power_level_low / 100.0)

    def interpolatePower(self):
        "Calculate energy consumption for the eud (in this case a linear interpolation) when the price is between price_dim_start and price_dim_end."
        power_reduction_ratio = (self._price - self._price_dim_start) / (self._price_dim_end - self._price_dim_start)
        power_level_percent = self._power_level_max - (self._power_level_max - self._power_level_low) * power_reduction_ratio
        return self._max_power_use * power_level_percent / 100.0


