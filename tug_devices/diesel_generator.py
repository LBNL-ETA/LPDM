"""
    Implementation of the Diesel Generator device.
"""
from device import Device
import logging

class DieselGenerator(Device):
    """
        Device implementation of a diesel generator.

        Usage:
            Instantiate the class with a dictionary of configuration options.

            generator = DieselGenerator(configuration_options)

        Attributes:
            _device_name: Name of the device
            _fuel_tank_capacity: Fuel capacity (gallons)
            _fuel_level: Current fuel level (percent)
            _fuel_reserve: Percent of initial value that is goal for having when refuel schedules (%)
            _days_to_refuel: How many days until refuel
            _kwh_per_gallon: Power output of generator (kwh/gallon)
            _time_to_reassess_fuel:  Interval for calculating the trajectory of consumption (seconds)
            _fuel_price_change_rate: Ceiling for fuel price change (%)
            _gen_eff_zero: generator efficiency (%) at zero output
            _gen_eff_100: generator efficiency (%) at 100% output
            _price_reassess_time: interval for reassessing price (seconds)
            _fuel_base_cost: Base cost of fuel ($/gallon)

            _current_fuel_price: current price of fuel ($/W-sec)

            _start_hour_consumption: The start time for tracking the hourly consumption
            _consumption_activity: Array that tracks the changes in consumption
            _consumption_24hr: Keeps track of the last 24 hours of diesel consumption by hour

            _last_fuel_status_time: Time when the last fuel status was calculated
            _target_refuel_time_secs: Time in seconds when the next refuel is expected
            _events: Upcoming events that are to be processed


    """
    def __init__(self, config = None):
        """
        Example:
            generator = DieselGenerator(config)

        Args:
            config (dict): Dictionary of default configuration values

                Valid Keys:

                "fuel_tank_capacity" (float): Capacity of the fuel tank in gallons.
                "fuel_level" (float): The current fuel level expressed as a percentage of the initial value (0 - 100)
                "fuel_reserve" (float): Percent of initial value that is goal for having when refuel schedules (%)
                "days_to_refuel" (int): How many days until refuel
                "kwh_per_gallon" (float): Power output of the generator (kWh/gallon)
                "time_to_reassess_fuel" (int): Interval for calculating the trajectory of consumption (seconds)
                "fuel_price_change_rate" (float): Maximum change amount for a change in fuel price change (%)
                "capacity" (float): the Maximum output capacity (Watts)
                "gen_eff_zero" (float): Generator efficiency at zero output (%)
                "gen_eff_100" (float): Generator efficiency at 100% output (%)
                "price_reassess_time" (int): Interval for reassessing price (seconds)
                "fuel_base_cost" (float): Base cost of fuel ($/gallon)
        """
        # set the properties specific to a diesel generator
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "diesel_generator"
        self._fuel_tank_capacity = config["fuel_tank_capacity"] if type(config) is dict and "fuel_tank_capacity" in config.keys() else 100.0 # fuel capacity (gallons)
        self._fuel_level = config["fuel_level"] if type(config) is dict and "fuel_level" in config.keys() else None     # current fuel level (percent)
        self._fuel_reserve = config["fuel_reserve"] if type(config) is dict and "fuel_reserve" in config.keys() else None   # percent of initial value that is goal for having when refuel schedules (%)
        self._days_to_refuel = config["days_to_refuel"] if type(config) is dict and "days_to_refuel" in config.keys() else None # how many days until refuel
        self._kwh_per_gallon = config["kwh_per_gallon"] if type(config) is dict and "kwh_per_gallon" in config.keys() else None # power output of generator (kwh/gallon)
        self._time_to_reassess_fuel = config["time_to_reassess_fuel"] if type(config) is dict and "time_to_reassess_fuel" in config.keys() else None  # interval for calculating the trajectory of consumption (seconds)
        self._fuel_price_change_rate = config["fuel_price_change_rate"] if type(config) is dict and "fuel_price_change_rate" in config.keys() else None # ceiling for fuel price change (%)
        self._capacity = config["capacity"] if type(config) is dict and "capacity" in config.keys() else 2000.0   # Generation capacity (Watts)
        self._gen_eff_zero = config["gen_eff_zero"] if type(config) is dict and "gen_eff_zero" in config.keys() else 0.0   #generator efficiency (%) at zero output
        self._gen_eff_100 = config["gen_eff_100"] if type(config) is dict and "gen_eff_100" in config.keys() else 100.0    #generator efficiency (%) at 100% output. Efficiency at some percentage is linear between _gen_eff_zero and _gen_eff_100
        self._price_reassess_time = config["price_reassess_time"] if type(config) is dict and "price_reassess_time" in config.keys() else None    # interval for reassessing price (seconds)
        # self._elec_price_change_rate = config["elec_price_change_rate"] if type(config) is dict and "elec_price_change_rate" in config.keys() else None # celing for price change (%)
        self._fuel_base_cost = config["fuel_base_cost"] if type(config) is dict and "fuel_base_cost" in config.keys() else None # base cost of fuel ($/gallon)

        self._current_fuel_price = config["current_fuel_price"] if type(config) is dict and "current_fuel_price" in config.keys() else None # current price of fuel ($/W-sec)

        self._start_hour_consumption = 0 # time when the last consumption calculation occured
        self._consumption_activity = []    #track the consumption changes for the hour
        self._consumption_24hr = [] # keeps track of the last 24 hours of diesel consumption by hour

        self._last_fuel_status_time = 0
        self._events = []

        self._target_refuel_time_secs = None
        self._base_refuel_time_secs = 0
        self.setTargetRefuelTime()

        self._scarcity_multiplier = 1.0

        self._power_level = 0.0

        self._time_price_last_update = 0

        # call the super constructor
        Device.__init__(self, config)

        # set the units for a deisel generator
        self._units = 'MW'


        # load a set of attribute values if a 'scenario' key is present
        if type(config) is dict and 'scenario' in config.keys():
            self.setScenario(config['scenario'])

        # Setup the next events for the device
        self.setNextHourlyConsumptionCalculationEvent()
        self.setNextReassesFuelChangeEvent()
        self.setNextRefuelEvent()
        
        self.calculateNextTTIE()

        # self._tasks = config["tasks"] if type(config) is dict and "tasks" in config.keys() else None
        # self._setupDeviceTasks()

    def status(self):
        return {
            "type": "diesel_generator",
            "in_operation": self._in_operation,
            "fuel_price": self._current_fuel_price,
            "power_level": self._power_level,
            "output_capcity": self.currentOutputCapacity(),
            "generation_rate": self.getCurrentGenerationRate(),
            "fuel_level": self._fuel_level            
        }

    def refresh(self):
        "Refresh the diesel generator."
        print('refresh the generator')
        self.removeRefreshEvents()
        self.setTargetRefuelTime()
        self.setNextRefuelEvent()

        self.updateFuelLevel()
        self.calculateElectricityPrice()
        self.reassesFuel()
        self.calculateNextTTIE()
        print(self._events)

    def removeRefreshEvents(self):
        "Remove events that need to be recalculated when the device status is refreshed.  For the diesel generator this is just the refuel event."
        next_refuels = []
        for event in self._events:
            if event['operation'] == 'refuel':
                print(event)
                next_refuels.append(event)

        for event in next_refuels:
            self._events.remove(event)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured (W)"
        # self.logMessage("Power change received (t = {0}, p = {1})".format(time, new_power), logging.INFO)

        if target_device_id == self._device_id:
            self._time = time
            if new_power > 0 and not self.isOn() and self._fuel_level > 0:
                # If the generator is not in operation the turn it on
                self.turnOn()
                self._power_level = new_power
                self.tugLogAction(action="turn_on", is_initial_event=False, value=self._power_level, description="W")

                # calculate the new electricity price
                self.calculateElectricityPrice(is_initial_event=False)

                # set to re calculate a new price
                self.setNextPriceChangeEvent()
                
                self.calculateNextTTIE()

                # store the new power consumption for the hourly usage calculations
                self.logPowerChange(time, new_power)

            elif new_power > 0 and self.isOn() and self._fuel_level > 0:
                # power has changed when already in operation
                # store the new power value for the hourly usage calculation
                self._power_level = new_power
                self.tugLogAction(action="power_change", is_initial_event=False, value=self._power_level, description="W")
                self.logPowerChange(time, new_power)
                self.calculateElectricityPrice(is_initial_event=False)

            elif new_power == 0 and self.isOn():
                # Shutoff power
                self.turnOff()
                self._power_level = 0.0
                self.tugLogAction(action="turn_off", is_initial_event=False, value=self._power_level, description="W")
                self.logPowerChange(time, 0.0)
        return

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        return

    def onTimeChange(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self.processEvents()
        self.calculateNextTTIE()
        return

    def setNextHourlyConsumptionCalculationEvent(self):
        "Setup the next event for the calculation of the hourly consumption"
        self._events.append({"time": self._time + 60 * 60, "operation": "hourly_consumption"})
        return

    def setNextPriceChangeEvent(self):
        "Setup the next event for a price change"
        self._events.append({"time": self._time + 60, "operation": "price"})
        return

    def setNextReassesFuelChangeEvent(self):
        "Setup the next event for reassessing the fuel level"
        if self._time == 0:
            self._events.append({"time": self._time + 60 * 60 * 24, "operation": "reasses_fuel"})
        else:
            self._events.append({"time": self._time + 60 * 60 * 6, "operation": "reasses_fuel"})

        return

    def setNextRefuelEvent(self):
        self._events.append({"time": self._time + self._days_to_refuel * 3600.0 * 24.0, "operation": "refuel"})

    def logPowerChange(self, time, power):
        "Store the changes in power usage"
        self._consumption_activity.append({"time": time, "power": power})

    def processEvents(self):
        "Process any events that need to be processed"

        # print('process events at {0}'.format(self._time))
        remove_items = []
        for event in self._events:
            if event["time"] <= self._time:
                if event["operation"] == "price":
                    if self.isOn():
                        self.updateFuelLevel()
                        self.calculateElectricityPrice(is_initial_event=True)

                    self.setNextPriceChangeEvent()
                    remove_items.append(event)

                elif event["operation"] == "hourly_consumption":
                    self.calculateHourlyConsumption(is_initial_event=True)
                    
                    self.setNextHourlyConsumptionCalculationEvent()

                    remove_items.append(event)

                elif event["operation"] == "reasses_fuel":
                    self.reassesFuel()
                    self.setNextReassesFuelChangeEvent()
                    remove_items.append(event)

                elif event["operation"] == "refuel":
                    self.refuel()
                    self.setNextRefuelEvent()
                    remove_items.append(event)

        # remove the processed events from the list
        if len(remove_items):
            for event in remove_items:
                self._events.remove(event)

        return

    def calculateNextTTIE(self):
        "calculate the next TTIE - look through the pending events for the one that will happen first"
        ttie = None
        for event in self._events:
            if ttie == None or event["time"] < ttie:
                ttie = event["time"]

        if ttie != None and ttie != self._ttie:
            self.broadcastNewTTIE(ttie)
            self._ttie = ttie

        return

    def updateFuelLevel(self):
        "Update the fuel level"
        kwh_used = 0.0
        interval_start_time = self._time

        # calculate how much energy has been used since the fuel level was last updated
        for item in self._consumption_activity[::-1]:
            # print(item)
            if item["time"] < self._last_fuel_status_time:
                time_diff = (interval_start_time - self._last_fuel_status_time) / 3600.0
                kwh_used += item["power"] / 1000.0 * time_diff
                break
            else:
                time_diff = (interval_start_time - item["time"]) / 3600.0
                kwh_used += item["power"] / 1000.0 * time_diff
                interval_start_time = item["time"]

        kwh_per_gallon = self.getCurrentGenerationRate()
        gallons_used = kwh_used / kwh_per_gallon
        gallons_available = self._fuel_tank_capacity * (self._fuel_level / 100.0)
        new_gallons = gallons_available - gallons_used

        self._last_fuel_status_time = self._time
        new_fuel_level = new_gallons / self._fuel_tank_capacity * 100
        if new_fuel_level != self._fuel_level:
            self.tugLogAction(action="fuel_level", is_initial_event=False, value=self._fuel_level, description="%")
            # self.logMessage("Fuel level set (t = {0}, fuel_level = {1})".format(self._time, new_fuel_level))

        self._fuel_level = new_fuel_level

        if self._fuel_level <= 0:
            self.turnOff()
            self._power_level = 0.0
            self.broadcastNewPower(self._power_level)
        return

    def setDaysToRefuel(self, days_to_refuel):
        "Sets the number of days until refuel"
        self.logMessage("Set refuel days (t = {0}, days_to_refuel = {1})".format(self._time, days_to_refuel))

    def getCurrentGenerationRate(self):
        "Calculates the current generation rate in kwh/gallon"
        return self.getGenerationRate(self._fuel_level)

    def getGenerationRate(self, fuel_level):
        return (self._gen_eff_zero / 100.0 + (self._gen_eff_100 - self._gen_eff_zero) / 100.0 * (fuel_level / 100.0)) * self._kwh_per_gallon

    def getTotalEnergyAvailable(self):
        "Get the total energy available in the tank (current fuel tank level in gallons * kwh/gallon). return the value in watt-seconds"
        # return self._fuel_tank_capacity * (self._fuel_level / 100.0) * self.getCurrentGenerationRate() * (60 * 60 * 1000)
        return self._fuel_tank_capacity * (self._fuel_level / 100.0) * self.getCurrentGenerationRate()

    def calculateElectricityPrice(self, is_initial_event=False):
        "Calculate a new electricity price ($/W-sec), based on instantaneous part-load efficiency of generator"
        if self.okToCalculatePrice():
            self._time_price_last_update = self._time
            new_price = self._fuel_base_cost / self.getCurrentGenerationRate() * self._scarcity_multiplier
            if self._current_fuel_price and abs(new_price - self._current_fuel_price) / self._current_fuel_price > (self._fuel_price_change_rate / 100.0):
                new_price = self._current_fuel_price + ((self._current_fuel_price * (self._fuel_price_change_rate / 100.0)) * (1 if new_price > self._current_fuel_price else -1))

            # print("fuel_level = {0}, gen_rate = {1}, price = {2}, base_cost = {3}, raw_calc = {4}".format(self._fuel_level, self.getCurrentGenerationRate(), new_price, self._fuel_base_cost, self._fuel_base_cost / self.getTotalEnergyAvailable()))
            if new_price != self._current_fuel_price:
                self._current_fuel_price = new_price

                self.tugLogAction(action="new_electricity_price", is_initial_event=is_initial_event, value=self._current_fuel_price, description="$/kWh")
                self.tugLogAction(action="fuel_level", is_initial_event=False, value=self._fuel_level, description="%")
                self.tugLogAction(action="generation_rate", is_initial_event=False, value=self.getCurrentGenerationRate(), description="kwh/gallon")
                self.tugLogAction(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")

                self.broadcastNewPrice(new_price)

        return

    def okToCalculatePrice(self):
        "Check if enough time has passed to recalculate the price"
        return self._time - self._time_price_last_update > self._price_reassess_time

    def getPrice(self):
        "Get the current fuel price"
        return self._current_fuel_price

    def calculateHourlyConsumption(self, is_initial_event=False):
        "Calculate and store the hourly consumption, only keeping the last 24 hours"
        total_kwh = 0.0
        interval_start_time = self._time

        # calculate how much energy has been used since the fuel level was last updated
        for item in self._consumption_activity[::-1]:
            if item["time"] < self._start_hour_consumption:
                time_diff = (interval_start_time - self._start_hour_consumption) / 3600.0
                total_kwh += item["power"] / 1000.0 * time_diff
                break
            else:
                time_diff = (interval_start_time - item["time"]) / 3600.0
                total_kwh += item["power"] / 1000.0 * time_diff
                interval_start_time = item["time"]


        # add the hourly consumption to the array
        self._consumption_24hr.append({"time": self._start_hour_consumption, "consumption": total_kwh})

        # set the time the hourly energy sum was last calculated
        self._start_hour_consumption = self._time
        
        # if we have more than 24 entries, remove the oldest entry
        if len(self._consumption_24hr) > 24:
            self._consumption_24hr.pop(0)
        
        sum_24hr = 0.0
        for item in self._consumption_24hr:
            sum_24hr += item["consumption"]

        self.tugLogAction(action="consumption_hr", is_initial_event=is_initial_event, value=total_kwh, description="kwh")
        self.tugLogAction(action="consumption_24hrs", is_initial_event=is_initial_event, value=sum_24hr, description="kwh")

        return

    def setTargetRefuelTime(self):
        "Set the next target refuel time (sec)"
        self._target_refuel_time_secs = self._base_refuel_time_secs + (self._days_to_refuel * 24 * 60 * 60) if self._days_to_refuel != None else None

    def refuel(self):
        "Refuel"
        self._base_refuel_time_secs = self._time
        self.setTargetRefuelTime()

        self._fuel_level = 100.0
        self._scarcity_multiplier = 1.0
        self.tugLogAction(action="refuel", is_initial_event=True, value=None)
        self.calculateElectricityPrice(is_initial_event=False)

    def reassesFuel(self, is_initial_event=False):
        "Calculate the scarcity multiplier"

        # calculate the last 24 hours of fuel consumption
        sum_24hr = 0.0
        for item in self._consumption_24hr:
            sum_24hr += item["consumption"]

        if sum_24hr > 0.0:
            # calculate the average amount of fuel used (fuel use at current time, fuel use when at reserve level)
            gallons_used = sum_24hr / self.getCurrentGenerationRate()
            gallons_used_at_reserve_level = sum_24hr / self.getGenerationRate(self._fuel_reserve)
            gallons_used_avg = (gallons_used + gallons_used_at_reserve_level) / 2.0

            # gallons when at reserve
            reserve_fuel_gallons = self._fuel_tank_capacity * (self._fuel_reserve / 100.0)

            # gallons currently in tank
            current_fuel_gallons = self._fuel_tank_capacity * (self._fuel_level / 100.0)

            # time in hours when refuelling occurs
            time_until_refuel_hrs = (self._target_refuel_time_secs - self._time) / 3600.0

            # estimate how many gallons would have been used when have reached the refuel time
            total_usage_at_refuel = time_until_refuel_hrs * (gallons_used_avg / 24.0)

            # estimated fuel level at time of refuel
            fuel_level_at_refuel = current_fuel_gallons - total_usage_at_refuel

            # calculate how far we are off from a fuel level at the reserve level
            trajectory = ((fuel_level_at_refuel - reserve_fuel_gallons) / reserve_fuel_gallons) * 100.0

            if trajectory < -10.0:
                # if off by more than 10% then increaes the scarcity multiplier by 5% (fuel level is estimated to be below the reserve_level by 10%)
                self._scarcity_multiplier = self._scarcity_multiplier * 1.05
            elif trajectory > 10.0:
                # decrease the multiplier by 5% if the estimated fuel level would be above the reserve level by 10%
                self._scarcity_multiplier = self._scarcity_multiplier * 0.95
                if self._scarcity_multiplier < 1.0:
                    self._scarcity_multiplier = 1.0

            self.tugLogAction(action="reasses_fuel", is_initial_event=is_initial_event, value=self._fuel_level, description="%")
            self.tugLogAction(action="scarcity_multiplier", is_initial_event=False, value=self._scarcity_multiplier, description="")
            self.tugLogAction(action="output_capacity", is_initial_event=False, value=self.currentOutputCapacity(), description="%")

            # self.logMessage("Set scarcity multiplier (t = {0}, scarcity mult = {1}".format(self._time, self._scarcity_multiplier))
        return

    def currentOutputCapacity(self):
        "Gets the current output capacity (%)"
        return 100.0 * self._power_level / self._capacity

