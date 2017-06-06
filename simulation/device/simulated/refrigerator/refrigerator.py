

################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0"
# Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

"""
    Implementation of an refrigerator
"""


from device.base.device import Device
from device.scheduler import LpdmEvent
import logging

class Refrigerator(Device):
    """
        Device implementation of a Refrigerator
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the refrigerator

                keys:
                    "device_type" (string): Type of device
                    "device_name" (string): Name of the device
                    "max_power_use" (float): the maximum power output of the device
                    "current_temperature" (float): the current temperature inside the device
                    "current_set_point (float)": the initial set point
                    "temperature_max_delta" (float): the maximum variation between the setpoint and actual temperature for every reassesment
                    "temperature_increment" (float): the maximum amount that the temperature can increase by for every reassessment
                    "set_point_low" (float): the low value for the set point
                    "set_point_high" (float): the high value for the set point
                    "setpoint_reassesment_interval" (int): number of seconds between reassesing the set point
        """


        Device.__init__(self, config)

        self._device_type = "refrigerator"
        self._device_name = config["device_name"] if type(config) is dict and "device_name" in config.keys() else "refrigerator"

        # maximim power output, set to 3500 W if no value given
        self._max_power_use = float(config["max_power_use"]) if type(config) is dict and "max_power_use" in config.keys() else 147

        self._fuel_price = None

        # set the nominal price to be price of first hour of generation
        self._nominal_price = None
        self._nominal_price_calc_running = False
        self._nominal_price_list = []

        # hourly average price tracking
        self._hourly_prices = []
        self._hourly_price_list = []

        self._current_temperature = float(config["current_temperature"]) if type(config) is dict and "current_temperature" in config.keys() else 3
        self._current_set_point = float(config["current_set_point"]) if type(config) is dict and "current_set_point" in config.keys() else 3
        self._temperature_max_delta = float(config["temperature_max_delta"]) if type(config) is dict and "temperature_max_delta" in config.keys() else 0.5
        self._temperature_increment = float(config["temperature_increment"]) if type(config) is dict and "temperature_increment" in config.keys() else 0.5
        self._set_point_low = float(config["set_point_low"]) if type(config) is dict and "set_point_low" in config.keys() else 0.5
        self._set_point_high = float(config["set_point_high"]) if type(config) is dict and "set_point_high" in config.keys() else 5.0
        self._setpoint_reassesment_interval = float(config["setpoint_reassesment_interval"]) if type(config) is dict and "setpoint_reassesment_interval" in config.keys() else 60.0 * 10.0

        self._time_price=0


        if type(config) is dict and "set_price_schedule" in config.keys() and type(config["set_price_schedule"]) is list:
            self._set_point_schedule = config["set_price_schedule"]
        else:
            self._set_price_schedule = self.default_price_schedule()

        self._time=0
        self._temperature_update_interval = 60.0 * 60.0
        self._current_outdoor_temperature = None
        self._last_temperature_update_time = self._time
        self._T_in_r = 276
        self._T_in_f = 255
        self.limitupper_f = 255.5
        self.limitupper_r = 276.5
        self.limitlower_f = 254.5
        self.limitlower_r = 275.5
        self._price_range_high = 0.1 # this is the price of battery energy
        self._current_temperature_r = 276
        self._current_temperature_f = 255
        self._current_set_point_f = 255
        self._current_set_point_r = 276
        self._T_first_f = 255
        self._T_first_r = 276
        self._set_point_factor = 44

        self._set_point_target = self._current_set_point
        self._setpoint_freezer_reached=0
        self._setpoint_refrigerator_reached=0
        self._sum_area=1855.86
        self._delta_time=600 # time between two change sin price
        self._medium_power =115 # compressor power in medium mode [W]
        self._high_power=147 # compressor power in high mode [W]
        self._low_power=70 # compressor power in low mode [W]

        self._T_initial_f=255
        self._T_max_f=260
        self._range_temp_f=10
        self._m_fr=13 # mass of food in the freezer

        self._T_initial_r=276
        self._T_max_r=277.5
        self._range_temp_r=3
        self._m_ref=20 # mass of the food in the refrigerator

        self.comp='off'
        self.comp_r='dis'
        self.comp_f='dis'

        self._disp_r=40 # heat loss refrigerator [W]
        self._disp_f=26.93 # heat loss freezer [W]

        self._rateup_r=((self._disp_r*3600)/(self._m_ref*2859.4+0.4*1030))/3600
        self._rateup_f=((self._disp_f*3600)/(self._m_fr*2200+0.13*1030))/3600
        self._ratedown_r=(((180-self._disp_r)*3600)/(self._m_ref*2859.4+0.4*1030))/3600 # when both evaporators work and no PCM is freezing , mediumk power 110.76 W
        self._ratedown_f=(((78.5-self._disp_f)*3600)/(self._m_fr*2200+0.13*1030))/3600 #
        self._ratedown_u_r=(((269-self._disp_r)*3600)/(self._m_ref*2859.4+0.4*1030))/3600 # it is 6 degrees also in the freezer alone because we change spped compressor operation --> low when freezer only
        self._ratedown_u_f=(((110-self._disp_f)*3600)/(self._m_fr*2200+0.13*1030))/3600


    # def init(self):
        # self.scheduleNextTemperatureChange()


    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured"
        self._time = time
        return

    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        "Receives messages when a power change has occured"
        return

    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        if not self._static_price:
            self._logger.debug(self.build_message(
                message="received new price",
                tag="receive_price",
                value=new_price
            ))

            if self._nominal_price is None:
                if not self._nominal_price_calc_running:
                    # if the nominal price has not be calculated or is not running
                    # then schedule the event and log the prices
                    self.set_nominal_price_calculation_event()
                self._nominal_price_list.append(new_price)

            # add the price to the list of prices for the hourly avg calculation
            self._hourly_price_list.append(new_price)
            self.set_new_fuel_price(new_price)
            return

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time
        self.process_events()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def default_price_schedule(self):
     return [
         [0,0.1],
         [600,0.1],
         [1200,0.1],
         [1800,0.1],
         [2400,0.1],
         [3000,0.1],
         [3600,0.1],
         [4200,0.1],
         [4800,0.1],
         [5400,0.1],
         [6000,0.1],
         [6600,0.1],
         [7200,0.1],
         [7800,0.1],
         [8400,0.1],
         [9000,0.1],
         [9600,0.1],
         [10200,0.1],
         [10800,0.1],
         [11400,0.1],
         [12000,0.1],
         [12600,0.1],
         [13200,0.1],
         [13800,0.1],
         [14400,0.1],
         [15000,0.1],
         [15600,0.1],
         [16200,0.1],
         [16800,0.1],
         [17400,0.1],
         [18000,0.1],
         [18600,0.1],
         [19200,0.1],
         [19800,0.1],
         [20400,0.1],
         [21000,0.1],
         [21600,0.1],
         [22200,0.1],
         [22800,0.1],
         [23400,0.1],
         [24000,0.1],
         [24600,0.1],
         [25200,0.1],
         [25800,0.1],
         [26400,0.1],
         [27000,0.1],
         [27600,0.095],
         [28200,0.09],
         [28800,0.084],
         [29400,0.079],
         [30000,0.074],
         [30600,0.069],
         [31200,0.064],
         [31800,0.06],
         [32400,0.055],
         [33000,0.051],
         [33600,0.046],
         [34200,0.042],
         [34800,0.038],
         [35400,0.035],
         [36000,0.031],
         [36600,0.028],
         [37200,0.025],
         [37800,0.022],
         [38400,0.02],
         [39000,0.017],
         [39600,0.015],
         [40200,0.014],
         [40800,0.012],
         [41400,0.011],
         [42000,0.011],
         [42600,0.01],
         [43200,0.01],
         [43800,0.01],
         [44400,0.011],
         [45000,0.011],
         [45600,0.012],
         [46200,0.014],
         [46800,0.015],
         [47400,0.017],
         [48000,0.02],
         [48600,0.022],
         [49200,0.025],
         [49800,0.028],
         [50400,0.031],
         [51000,0.035],
         [51600,0.038],
         [52200,0.042],
         [52800,0.046],
         [53400,0.051],
         [54000,0.055],
         [54600,0.06],
         [55200,0.064],
         [55800,0.069],
         [56400,0.074],
         [57000,0.079],
         [57600,0.084],
         [58200,0.09],
         [58800,0.095],
         [59400,0.1],
         [60000,0.1],
         [60600,0.1],
         [61200,0.1],
         [61800,0.1],
         [62400,0.1],
         [63000,0.1],
         [63600,0.1],
         [64200,0.1],
         [64800,0.1],
         [65400,0.1],
         [66000,0.1],
         [67200,0.1],
         [67800,0.1],
         [68400,0.1],
         [69000,0.1],
         [69600,0.1],
         [70200,0.1],
         [70800,0.1],
         [71400,0.1],
         [72000,0.1],
         [72600,0.1],
         [73200,0.1],
         [73800,0.1],
         [74400,0.1],
         [75000,0.1],
         [75600,0.1],
         [76200,0.1],
         [76800,0.1],
         [77400,0.1],
         [78000,0.1],
         [78600,0.1],
         [79200,0.1],
         [79800,0.1],
         [80400,0.1],
         [81000,0.1],
         [81600,0.1],
         [82200,0.1],
         [82800,0.1],
         [83400,0.1],
         [84000,0.1],
         [84600,0.1],
         [85200,0.1],
         [85800,0.1],
         [86400,0.1],
         ]





    def process_events(self):
        "Process any events that need to be processed"
        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "set_nominal_price":
                    self.calculate_nominal_price()
                    remove_items.append(event)
                elif event.value == "hourly_price_calculation":
                    self.calculate_hourly_price()
                    remove_items.append(event)
                elif event.value == "freezer_setpoint_reached" or event.value=="refrigerator_setpoint_reached" or event.value=="reasses_setpoint":
                    self.adjust_internal_temperature()
                    self.control_compressor_operation()
                    if event.value=="reasses_setpoint":
                     self.reasses_setpoint()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

        return
    # still have to create a function which determines the freezer setpoint and refrigerator setpoint time

    def set_nominal_price_calculation_event(self):
        """
        calculate the nominal price using the avg of the first hour of operation
        so once the first price shows up start keeping track of the prices, then
        an hour later calculate the avg.
        """
        self._events.append(LpdmEvent(self._time_price + 60.0 * 10.0, "set_nominal_price"))
        self._nominal_price_list = []
        self._nominal_price_calc_running = True
        self._time_price=self._time_price+600.0

    def calculate_nominal_price(self):
        if not self._nominal_price_calc_running:
            raise Exception("Nominal price calculation has not been started")

        self._nominal_price_calc_running = False
        #self._nominal_price = sum(self._nominal_price_list) / float(len(self._nominal_price_list))

        schedule_item = self._set_price_schedule[int(self._time/145)]
        if type(schedule_item) is list and len(schedule_item) == 2:
            self._nominal_price= schedule_item[1]


        else:
            self._logger.error(
                       self.build_message(
                                          message="the setpoint schedule item ({0}) is not in the correct format - [hour, low, high]".format(schedule_item),
                                          )
                       )
            raise Exception("Invalid setpoint schedule item {}".format(schedule_item))
        self._logger.info(self.build_message("Request to calculate nominal price"))

    def schedule_next_events(self):
        Device.schedule_next_events(self)
        #"Schedule upcoming events if necessary"
        # set the event for the hourly price calculation and setpoint reassesment
        self.set_hourly_price_calculation_event()
        self.set_reasses_setpoint_event()
        self.setpoint_reached_time()
        return

    def set_hourly_price_calculation_event(self):
        #"set the next event to calculate the avg hourly prices"
        new_event = LpdmEvent(self._time + 60.0 * 60.0, "hourly_price_calculation")
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)
            self._hourly_price_list = []

    def set_reasses_setpoint_event(self):
        #"set the next event to calculate the set point"
        new_event = LpdmEvent(self._time + self._setpoint_reassesment_interval, "reasses_setpoint")
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def set_reasses_freezer_setpoint_reached(self):
        #"set the next event to calculate the set point"
        new_event = LpdmEvent(self._time + self._setpoint_freezer_reached, "freezer_setpoint_reached" )
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)
    def set_reasses_refrigerator_setpoint_reached(self):
        #"set the next event to calculate the set point"
        new_event = LpdmEvent(self._time + self._setpoint_refrigerator_reached, "refrigerator_setpoint_reached" )
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == new_event.value, self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def setpoint_reached_time(self):

      if self.comp == 'off':

        self._setpoint_freezer_reached=(self.limitupper_f-self._current_temperature_f)/self._rateup_f #Time needed to freezer to reach the set point

        self._setpoint_refrigerator_reached=(self.limitupper_r-self._current_temperature_r)/self._rateup_r #Time needed to freezer to reach the set point

#self._logger.info(self.build_message(self.limitupper_f,self._current_temperature_f,"off"))

      elif self.comp == 'on':

        self._setpoint_freezer_reached=(self._current_temperature_f-self.limitlower_f)/self._ratedown_f #Time needed to freezer to reach the set point

        self._setpoint_refrigerator_reached=(self._current_temperature_r-self.limitlower_r)/self._ratedown_r #Time needed to freezer to reach the set point

        #self._logger.info(self.build_message(self.limitlower_f,self.limitlower_r,"on"))

      elif self.comp_r =='off': # compressor is on just for the freezer


        self._setpoint_freezer_reached=(self._current_temperature_f-self.limitlower_f)/self._ratedown_u_f #Time needed to freezer to reach the set point

        self._setpoint_refrigerator_reached=(self.limitupper_r-self._current_temperature_r)/self._rateup_r  #Time needed to freezer to reach the set point

#self._logger.info(self.build_message(self.limitlower_f,self._current_temperature_f,"r-off"))

      elif self.comp_f=='off':

        self._setpoint_freezer_reached=(self.limitupper_f-self._current_temperature_f)/self._rateup_f #Time needed to freezer to reach the set point

        self._setpoint_refrigerator_reached=(self._current_temperature_r-self.limitlower_r)/self._ratedown_u_r #Time needed to freezer to reach the set point

#self._logger.info(self.build_message("f-off"))

      if self._setpoint_freezer_reached <= self._setpoint_refrigerator_reached:

          self.set_reasses_freezer_setpoint_reached()
      else:

          self.set_reasses_refrigerator_setpoint_reached()


    def calculate_hourly_price(self):
        """This should be called every hour to calculate the previous hour's average fuel price"""
        hour_avg = None
        if len(self._hourly_price_list):
            hour_avg = sum(self._hourly_price_list) / float(len(self._hourly_price_list))
        elif self._fuel_price is not None:
            hour_avg = self._fuel_price

        self._hourly_prices.append(hour_avg)
        if len(self._hourly_prices) > 24:
            # remove the oldest item if more than 24 hours worth of data
            self._hourly_prices.pop(0)

        self._hourly_price_list = []

    def set_new_fuel_price(self, new_price):
        """Set a new fuel price"""
        self._fuel_price = new_price

    def reasses_setpoint(self):
        """determine the setpoint based on the current price and 24 hr. price history"""

        # check to see if there's 24 hours worth of data, if there isn't exit
#        if len(self._hourly_prices) < 24:
#            return
#
#        # determine the current price in relation to the past 24 hours of prices
#        sorted_hourly_prices = sorted(self._hourly_prices)
#        for i in xrange(24):
#            if  self._fuel_price < sorted_hourly_prices[i]:
#                break
#
#        price_percentile = float(i + 1) / 24.0
#        new_setpoint = self._set_point_low + (self._set_point_high - self._set_point_low) * price_percentile
#        if new_setpoint != self._current_set_point:
#            self._current_set_point = new_setpoint
#            self.logMessage("calculated new setpoint as {}".format(new_setpoint))

        if self._nominal_price >= 0.1:

            # price > price_range_high, then setpoint to max plus (price - price_range_high)/5
            self.new_setpoint_r = self._current_set_point_r + (self._T_max_r - self._T_first_r) / self._set_point_factor # new setpoint of the refrigerator compartment
            self.new_setpoint_f = self._current_set_point_f + (self._T_max_f - self._T_first_f) / self._set_point_factor # new setpoint of the freezer compartment
            self._logger.info(self.build_message(self.new_setpoint_r,self.new_setpoint_f,self._nominal_price))

        elif self._nominal_price < 0.1:
            # fuel_price_low < fuel_price < fuel_price_high
            # new setpoint is relative to where the current price is between price_low and price_high
            self.new_setpoint_r = self._current_set_point_r -self._range_temp_r*((self._delta_time)*(0.1-self._price)/self._sum_area)
            self.new_setpoint_f = self._current_set_point_f -self._range_temp_f*((self._delta_time)*(0.1-self._price)/self._sum_area)
            self._logger.info(self.build_message(self.new_setpoint_r,self.new_setpoint_f,self._nominal_price))
        self.limitlower_f=self.new_setpoint_f-0.5
        self.limitupper_f=self.new_setpoint_f+0.5
        self.limitlower_r=self.new_setpoint_r-0.5
        self.limitupper_r=self.new_setpoint_r+0.5
#        else:
#            # price < price_range_low
#            new_setpoint = self._set_point_low

        # self.logMessage('reassesSetpoint: Refrigerator current setpoint = {}, new setpoint = {}'.format(self._current_set_point_r, new_setpoint_r));
        # self.logMessage('reassesSetpoint: Freezer current setpoint = {}, new setpoint = {}'.format(self._current_set_point_f, new_setpoint_f));
        if self.new_setpoint_r != self._current_set_point_r and self.new_setpoint_f != self._current_set_point_f:
            self._current_set_point_r = self.new_setpoint_r
            self._current_set_point_f = self.new_setpoint_f
            # self.logMessage("calculated new refrigerator setpoint as {}".format(new_setpoint_r))
            # self.logMessage("calculated new freezer setpoint as {}".format(new_setpoint_f))
#        if self._current_set_point < 1000:
#            self.logPlotValue("set_point", self._current_set_point)
#        if self.time<=86400:
#             self._current_set_point_r=276
#              self._current_set_point_f=255
#              self.limitlower_f=255-0.5
#              self.limitupper_f=255+0.5
#              self.limitlower_r=276-0.5
#              self.limitupper_r=276+0.5

    def adjust_internal_temperature(self):
        """
        adjust the temperature of the two compartments: refrigerator and freezer depending on the status of compressor
        """
        if self._time > self._last_temperature_update_time:
            if self.comp=='off':
                #energy_used = self._medium_power * (self._time - self._last_temperature_update_time)
                self.power=self._medium_power
                T_in_f=self._current_temperature_f+(self._time - self._last_temperature_update_time)*self._ratedown_f
                # self.logMessage("Freezer internal temperature changed from {} to {}".format(self._current_temperature_f,T_in_f))
                self._current_temperature_f=T_in_f
                T_in_r=self._current_temperature_r+(self._time - self._last_temperature_update_time)*self._ratedown_r
                # self.logMessage("Refrigerator internal temperature changed from {} to {}".format(self._current_temperature_r,T_in_r))
                self._current_temperature_r=T_in_r

                self._logger.info(self.build_message(self._current_temperature_f))
#                delta_c = self._compressor_max_c_per_kwh * energy_used
                #self._current_temperature -= delta_c
                #self.logMessage("calculated compressors decrease of C to {}".format(delta_c))
            if self.comp=='on':
                #energy_used = self._medium_power * (self._time - self._last_temperature_update_time) / 3600.0
                T_in_f=self._current_temperature_f-(self._time - self._last_temperature_update_time)*self._rateup_f
                # self.logMessage("Freezer internal temperature changed from {} to {}".format(self._current_temperature_f,T_in_f))
                self._current_temperature_f=T_in_f
                T_in_r=self._current_temperature_r-(self._time - self._last_temperature_update_time)*self._rateup_r
                # self.logMessage("Refrigerator internal temperature changed from {} to {}".format(self._current_temperature_r,T_in_r))
                self._current_temperature_r=T_in_r


            if self.comp_f=='off': # only refrigerator evaporator works
                #energy_used = self._medium_power * (self._time - self._last_temperature_update_time)
                self.power=self._medium_power
                T_in_f=self._current_temperature_f+(self._time - self._last_temperature_update_time)*self._rateup_f
                # self.logMessage("Freezer internal temperature changed from {} to {}".format(self._current_temperature_f,T_in_f))
                self._current_temperature_f=T_in_f
                T_in_r=self._current_temperature_r-(self._time - self._last_temperature_update_time)*self._ratedown_u_r
                # self.logMessage("Refrigerator internal temperature changed from {} to {}".format(self._current_temperature_r,T_in_r))
                self._current_temperature_r=T_in_r

            if self.comp_r=='off':
                #energy_used = self._low_power * (self._time - self._last_temperature_update_time)
                self.power=self._low_power
                T_in_f=self._current_temperature_f-(self._time - self._last_temperature_update_time)*self._ratedown_u_f
                # self.logMessage("Freezer internal temperature changed from {} to {}".format(self._current_temperature_f,T_in_f))
                self._current_temperature_f=T_in_f
                T_in_r=self._current_temperature_r+(self._time - self._last_temperature_update_time)*self._rateup_r
                # self.logMessage("Refrigerator internal temperature changed from {} to {}".format(self._current_temperature_r,T_in_r))
                self._current_temperature_r=T_in_r

#            if not self._current_outdoor_temperature is None:
#                # difference between indoor and outdoor temp
#                delta_indoor_outdoor = self._current_outdoor_temperature - self._current_temperature
#                # calculate the fraction of the hour that has passed since the last update
#                scale = (self._time - self._last_temperature_update_time) / 3600.0
#                # calculate how much of that heat gets into the tent
#                c_change = delta_indoor_outdoor * self._heat_gain_rate * scale

#                self.logMessage("internal temperature changed from {} to {}".format(self._current_temperature, self._current_temperature + c_change))
#                self._current_temperature += c_change

            # update heat losses and rate of temperature increase and decrease
            self._disp_r=(293-self._T_in_r)/0.4375 # heat loss refrigerator [W]
            self._disp_f=(293-self._T_in_f)/1.41  # heat loss freezer [W]

            self._rateup_r=((self._disp_r*3600)/(self._m_ref*2859.4+0.4*1030))/3600
            self._rateup_f=((self._disp_f*3600)/(self._m_fr*2200+0.13*1030))/3600
            self._ratedown_r=(((180-self._disp_r)*3600)/(self._m_ref*2859.4+0.4*1030))/3600 # when both evaporators work and no PCM is freezing , mediumk power 110.76 W
            self._ratedown_f=(((78.5-self._disp_f)*3600)/(self._m_fr*2200+0.13*1030))/3600 #
            self._ratedown_u_r=(((269-self._disp_r)*3600)/(self._m_ref*2859.4+0.4*1030))/3600 # it is 6 degrees also in the freezer alone because we change spped compressor operation --> low when freezer only
            self._ratedown_u_f=(((110-self._disp_f)*3600)/(self._m_fr*2200+0.13*1030))/3600

            # self.logPlotValue("Refrigerator current_temperature", self._current_temperature_r)
            # self.logPlotValue("Freezer current_temperature", self._current_temperature_f)
            self._last_temperature_update_time = self._time



    def control_compressor_operation(self):
       if self._current_set_point is None:
            return


       if self.limitupper_f-self._current_temperature_f<=0 :
            # freezer reaches the upper limit, compressor must turne on
            if  self.comp=='off':

                self.comp='dis'
                self.comp_f='dis'
                self.comp_r='off' # only freezer evaporator works

            elif  self.comp=='off':

                self.turn_on()
                self.comp='on'
                self.comp_f='dis'
                self.comp_r='dis'
            self._logger.info(self.build_message("uno"))


       if self.limitupper_r-self._current_temperature_r<=0 :
            # refrigerator reaches the upper limit, compressor must turne on
            if self.comp=='off':

               self.comp='dis'
               self.comp_f='off'
               self.comp_r='dis'

            elif self.comp_r =='off':

               self.comp='on'
               self.comp_f='dis'
               self.comp_r='dis'
            self._logger.info(self.build_message("due"))

       if self._current_temperature_f-self.limitlower_f<=0 :
            # freezer reaches the lower limit, compressor must turne off
            if self.comp=='on':

               self.comp='dis'  # Qua ci sono due possibilita: quando il freezer raggiunge la temperatura minima stacco il compressor per entrambi
               self.comp_f='off' #anche se il frigo non ha raggiunto il setpoint minimo ( soluzione se vogliamo dare continuita al compressore)
               self.comp_r='dis'# Altrimenti se imposto comp_f= off stacco solo compressore freezer e seguo il setpoint del frigo, compressore puo essere acceso per poco pero
             #print(now)
            elif self.comp_r=='off': # era spento solo compressore refrigerator
             #print(now)
             self.comp='off'
             self.comp_f='dis'
             self.comp_r='dis'
            self._logger.info(self.build_message("tre"))

       if self._current_temperature_r-self.limitlower_r<=0:
            # refrigerator reaches the lower limit, compressor must turne off
            if self.comp=='on':

              self.comp='dis'
              self.comp_f='dis'
              self.comp_r='off'# spengo solo compressore frigo e non freezer
             #print(now)
            elif self.comp_f=='off':

              self.comp='off'
              self.comp_f='dis'
              self.comp_r='dis'
            self._logger.info(self.build_message("quattro"))


    # def schedule_next_temperature_change(self):
        # """schedule the next temperature update (in one hour)"""
        # # first search for existing events
        # search_events = [event for event in self._events if event.value == "update_temperature"]
        # if not len(search_events):
            # self._events.append({"time": self._time + self._temperature_update_interval, "operation": "update_temperature"})

    def process_temperature_change(self):
        """Update the current outdoor temperature"""
        # get the time of day in seconds
        time_of_day = self.time_of_day_seconds()
        found_temp = None
        for temp in self._temperature_hourly_profile:
            if temp["hour_seconds"] >= time_of_day:
                found_temp = temp
                break

        if found_temp:
            self.update_temperature(temp["value"])

    def sum_energy_used(self, power_level):
      self._total_energy_use += self._power * (self._time - self._last_total_energy_update_time) / (1000 * 3600)
      self._last_total_energy_update_time = self._time


    def update_temperature(self, new_temperature):
        #"This method needs to be implemented by a device if it needs to act on a change in temperature"
        self._current_outdoor_temperature = new_temperature
        # self.log_message("Outdoor temperature changed to {}".format(new_temperature))
        return


