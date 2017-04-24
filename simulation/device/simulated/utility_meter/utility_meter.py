

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
    Implementation of the Utility Meter device.
"""
from device.base.power_source import PowerSource
from device.scheduler import Scheduler

from common.smap_tools import download_most_recent_point

class UtilityMeter(PowerSource):
    """
        Device implementation of a utility meter.

        Usage:
            Instantiate the class with a dictionary of configuration options.

            meter = UtilityMeter(configuration_options)

        Attributes:
            _device_name: Name of the device


    """
    def __init__(self, config = None):
        """
        Example:
            meter = UtilityMeter(config)

        Args:
            config (dict): Dictionary of default configuration values

                Valid Keys:

                "capacity" (float): the Maximum output capacity (Watts)
                "current_fuel_price" (float): The initial price of fuel ($/kWh)
                "schedule" (list of (timestamp, int) pairs): Daily schedule of hours of operation.  1 is on, 0 is off.
        """
        # call the super constructor
        PowerSource.__init__(self, config)

        # set the properties specific to a utility meter
        self._capacity = config.get("capacity", 2000.0)
        self._power_price = config.get("power_price", 0.01)

        self._smap_info = config.get("smap", None)
        
        self._scheduler = None
        self._schedule_array = config.get("schedule", None)
        self._dr_level = 0
        
        #Just keeping this for reporting purposes.
        self._start_hour_consumption = 0 # time when the last consumption calculation occured
        self._consumption_activity = []    #track the consumption changes for the hour
        self._consumption_24hr = [] # keeps track of the last 24 hours of diesel consumption by hour

        # load a set of attribute values if a 'scenario' key is present
        if type(config) is dict and 'scenario' in config.keys():
            self.set_scenario(config['scenario'])

    def init(self):
        """Run any initialization functions for the device"""
        # Setup the next events for the device
        self.setup_schedule()
        self.make_unavailable()
        self.calculate_electricity_price()
        self.schedule_next_events()

        self.calculate_next_ttie()
        
    def check_dr(self):
        if self._smap_info:
                dr_stream_info = self._smap_info.get("dr", None)
                if dr_stream_info:
                    _, _, self._dr_level = download_most_recent_point(dr_stream_info["smap_root"], dr_stream_info["stream"])
            
        return self._dr_level

  

    def status(self):
        return {
            "type": "utility_meter",
            "in_operation": self._in_operation,
            "power_price": self.power_price,
            "power_level": self._power_level,
            "output_capcity": self.current_output_capacity()
        }

    def refresh(self):
        "Refresh the utility meter. Currently this means resetting the operation schedule."
        self._ttie = None
        self._next_event = None
        self._events = []

        self.setup_schedule()
        self.schedule_next_events()
        self.calculate_next_ttie()

    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        "Receives messages when a power change has occured (W)"

        if target_device_id == self._device_id:
            self._time = time
            self._logger.info(
                self.build_message(
                    message="received power change from {}, new_power = {}".format(source_device_id,  new_power),
                    tag="receive_power",
                    value=new_power
                )
            )
            if not self.is_available() and new_power > 0:
                # if the device has its capacity set to zero then not available, raise an excpetion unless the new power is also zero
                raise Exception("Attempt to set load on a power source that has no capacity available.")
            else:
                self.set_power_level(new_power)
                self.log_power_change(time, new_power)
                self.schedule_next_events()
                self.calculate_next_ttie()


    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        "Receives message when a price change has occured"
        return

    def on_time_change(self, new_time):
        "Receives message when time for an 'initial event' change has occured"
        self._time = new_time        
        self.calculate_electricity_price()
        self.calculate_capacity()
        self.process_events()
        return
    
    def set_power_level(self):
        """Override the base class method"""
        pass

    def set_power(self, power):
        """Set the power level for the device"""
        self._power_level = power
        self._logger.debug(
            self.build_message(
                message="Set new power level",
                tag="power",
                value=self._power_level
            )
        )

    def log_power_change(self, time, power):
        "Store the changes in power usage"
        self._consumption_activity.append({"time": time, "power": power})

    def calculate_electricity_price(self):        
        "Calculate a new electricity price ($/W-sec).  Starting as a static price"
        dr = self.check_dr()
#         if dr is None:
#             print "ERROR GETTING DR"
#         else:
#             print "*" * 12
#             print str(dr)
#             print "*" * 12
        price = self.get_price()
        price = price * (1 + dr)   
        self.broadcast_new_price(price, target_device_id=self._grid_controller_id)
        
    def calculate_capacity(self):
        "Calculate a new capacity.  Starting with configured capacity when on and 0 when off"
        self.broadcast_new_capacity(self.get_capacity(), target_device_id=self._grid_controller_id)

    def get_price(self):
        "Get the current power price"    
        if self._smap_info:
                price_stream_info = self._smap_info.get("price", None)
                if price_stream_info:
                    _, _, self._power_price = download_most_recent_point(price_stream_info["smap_root"], price_stream_info["stream"])
            
        return self._power_price
    
    def get_capacity(self):
        if self._smap_info:
            capacity_stream_info = self._smap_info.get("capacity", None)
            if capacity_stream_info:
                _, _, self._capacity = download_most_recent_point(capacity_stream_info["smap_root"], capacity_stream_info["stream"])
        
        return self._capacity

    def calculate_hourly_consumption(self, is_initial_event=False):
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

        # Log the messages
        self._logger.debug(
            self.build_message(
                message="consumption last hour = {}".format(total_kwh),
                tag="consump_hour_kwh",
                value=total_kwh
            )
        )
        self._logger.debug(
            self.build_message(
                message="consumption last 24 hours = {}".format(sum_24hr),
                tag="consump_24_hr_kwh",
                value=sum_24hr
            )
        )

    def current_output_capacity(self):
        "Gets the current output capacity (%)"
        return 100.0 * self._power_level / self._current_capacity

    def process_events(self):
        PowerSource.process_events(self)
        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "off" and self._current_capacity > 0:
                    self.make_unavailable()
                elif event.value == "on" and self._current_capacity == 0:
                    self.make_available()
                elif event.name == "price":
                    self.set_price(event.value)
                elif event.value == "emit_initial_price":
                    self.calculate_electricity_price()
                elif event.value == "emit_initial_capacity":
                    self.calculate_capacity()
                remove_items.append(event)

        for event in remove_items:
            self._events.remove(event)
        self.schedule_next_events()
        self.calculate_next_ttie()
        self.calculate_hourly_consumption()
