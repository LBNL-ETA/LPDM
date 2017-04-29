

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
    Implementation of a battery
"""

from device.base.power_source import PowerSource
from device.scheduler import LpdmEvent
from common.device_class_loader import DeviceClassLoader
import logging
from lpdm_exception import LpdmMissingPowerSourceManager, LpdmBatteryDischargeWhileCharging, \
        LpdmBatteryNotDischarging, LpdmBatteryAlreadyDischarging, LpdmBatteryCannotDischarge, \
        LpdmBatteryChargeWhileDischarging, LpdmBatteryAlreadyCharging
from state_preference import StatePreference

class Battery(PowerSource):
    """
        Device implementation of a battery.

        The battery is fully controlled by the grid controller, so there's no TTIE calculations;
        and it doesn't respond to any power, price, or time changes.

        Methods:
            start_charging: starts the battery charging,
            stop_charging: stops the battery charging,
            state_of_charge: gets the current SOC of the battery
    """

    def __init__(self, config):
        """
            Args:
                config (Dict): Dictionary of configuration values for the grid controller

                keys:
                    "device_name" (string): Name of the device
                    "capacity" (float): Capacity of the battery (kWh)
                    "current_soc" (float): Current fraction of capacity
                    "min_soc" (float): Fraction of capacity at which the battery wants to stop discharging
                    "max_soc" (float): Fraction of capacity at which the battery wants to stop charging
                    "max_charge_rate" (float): Max charge rate (Watts)
                    "roundtrip_eff" (float): Fraction of power that is stored and available for withdrawl
        """
        # call the super constructor
        PowerSource.__init__(self, config)

        if self._device_id is None:
            raise Exception("Battery requires a device_id")

        self._device_type = "battery"
        self._device_name = config.get("device_name", "battery")
        self._capacity = config.get("capacity", 5000.0)
        self._current_soc = config.get("current_soc", 1.0)
        self._min_soc = config.get("min_soc", 0.2)
        self._max_soc = config.get("max_soc", 0.8)
        self._max_charge_rate = config.get("max_charge_rate", 1000.0)
        self._roundtrip_eff = config.get("roundtrip_eff", 0.9)
        self._check_soc_rate = config.get("check_soc_rate", 300)
        self._min_soc_refresh_rate = 60
        self._discharge_price_threshold = config.get("discharge_price_threshold", 0.80)
        self._charge_price_threshold = config.get("charge_price_threshold", 0.20)

        self.power_source_manager = None

        self._current_capacity = None
        self._battery_on_time = None
        self._last_update_time = self._time
        self._charge_start_time = None
        self._can_charge = False
        self._is_charging = False
        self._can_discharge = False

        self._preference = None

        self._sum_charge_kwh = 0
        self._last_charge_update_time = 0

        # set up class loader
        self._device_class_loader = DeviceClassLoader()
        self._status_logic_class_name = config.get('status_logic_class_name', 'LogicA')
        self._status_logic = None

    def init(self):
        self.set_initial_preference()
        self.set_status_logic()
        self.update_status()
        self.schedule_next_events()

    def set_initial_preference(self):
        """Set the initial preference state of the battery (does it want to charge/discharge/nothing)"""
        self._preference = StatePreference.DISCHARGE;

    def set_status_logic(self):
        # get the class object from the class name
        LogicClass = self._device_class_loader.class_for_name(
            "device.simulated.battery.logic", self._status_logic_class_name
        )
        # create the object
        self._status_logic = LogicClass(self)
        self._logger.info(self.build_message("Set status logic class to {}".format(LogicClass)))

    def set_event_list(self, events):
        """Set the event list to one that has been passed in"""
        self._events = events

    def set_power_source_manager(self, psm):
        """Set the power source manager"""
        self.power_source_manager = psm

    def set_price_history(self, hourly_prices):
        """Set the hourly_price list (shared from the gc)"""
        self._hourly_prices = hourly_prices

    def get_load(self):
        """Get the current load on the battery"""
        return self._power_level

    def set_load(self, new_load):
        """Set the load of the battery"""
        if new_load > 0:
            if not self._can_discharge:
                raise LpdmBatteryCannotDischarge()
        elif new_load < 0:
            raise Exception("Battery will set its own load when recharging")
        if new_load != self._power_level:
            self.set_power_level(new_load)
            self._logger.info(
                self.build_message(
                    message="Set load to {}".format(self._power_level),
                    tag="power",
                    value=self._power_level
                )
            )

    def add_load(self, new_load):
        """Add load on to the battery. should only happen when discharging is enabled"""
        if new_load > 0 and not self._can_discharge:
            raise LpdmBatteryNotDischarging()
        if new_load < 0 and not self._can_charge:
            raise Exception("Battery is not set to charge")

        self._logger.debug(
            self.build_message(
                message="Added load to the battery ({})".format(new_load)
            )
        )
        self.set_power_level(self._power_level + new_load)

    def set_time(self, new_time):
        """Set the time"""
        self._time = new_time

    def capacity(self):
        "Return the capcity of the battery (W)"
        return self._capacity

    def on_power_change(self, time, new_power):
        "Receives messages when a power change has occured"
        return

    def on_price_change(self, new_price):
        "Receives message when a price change has occured"
        return

    def on_time_change(self, new_time):
        pass

    def calculate_next_ttie(self):
        pass

    def update_status(self):
        self._status_logic.update_status()

    def max_charge_rate(self):
        """Max rate that the battery can charge (W)"""
        return self._max_charge_rate

    def charge_rate(self):
        "The actual charge rate (W)"
        return self._max_charge_rate * self._roundtrip_eff

    def is_discharging(self):
        """Is the battery discharging?"""
        return self._can_discharge and self._power_level > 0

    def is_charging(self):
        """Is the battery charging?"""
        return self._is_charging

    def enable_discharge(self):
        """
        Set the capacity in the power source manager so it knows that the battery is ready to accept load
        """
        if self.is_charging():
            raise LpdmBatteryDischargeWhileCharging()
        elif self._can_discharge:
            raise LpdmBatteryAlreadyDischarging()
        else:
            self._logger.info(
                self.build_message(
                    message="enable discharge (soc = {})".format(self._current_soc),
                    tag="discharge",
                    value="1"
                )
            )
            self._can_discharge = True
            self.power_source_manager.set_capacity(self._device_id, self._capacity)

    def disable_discharge(self):
        """
        Stop discharging:
            set the capacity in the power source manager to 0 to mark it as unavailable
        """
        if not self._can_discharge:
            # raise an exception if there's an attempt to stop discharging if it isn't actually discharging
            raise LpdmBatteryNotDischarging()

        # if self.is_discharging():
            # self.stop_discharging()

        self._logger.debug(
            self.build_message(
                message="Disable discharge (soc = {})".format(self._current_soc),
                tag="discharge",
                value="0"
            )
        )
        self._can_discharge = False
        self.power_source_manager.set_capacity(self._device_id, 0.0)

    # def stop_discharging(self):
        # """Stop discharging the battery"""
        # print "stop discharring {}".format(self.is_discharging())
        # if self.is_discharging():
            # # set the load on the battery to zero
            # # also set the load in the power source manager to zero
            # self.power_source_manager.set_load(self._device_id, 0.0)

    def update_state_of_charge(self):
        """Update the state of charge"""
        if self._time - self._last_update_time > self._min_soc_refresh_rate:
            previous = self._current_soc
            if self.is_charging():
                self._current_soc = (
                    (self._capacity * self._current_soc)
                    + (self.charge_rate() * (self._time - self._last_update_time) / 3600.0)
                ) / (self._capacity)
            elif self._can_discharge and self._power_level > 0:
                self._current_soc = (
                    (self._capacity * self._current_soc)
                    - (self._power_level * (self._time - self._last_update_time) / 3600.0)
                ) / (self._capacity)

            if self._current_soc != previous:
                # log when the value changes
                self._logger.debug(self.build_message(message="soc", tag="soc", value=self._current_soc))
            self._last_update_time = self._time

    def enable_charge(self):
        """set the enable_charge flag to true """
        if self._can_discharge:
            raise LpdmBatteryChargeWhileDischarging()
        elif self._can_charge:
            raise LpdmBatteryAlreadyCharging()
        else:
            self._logger.info(
                self.build_message(
                    message="enable charge (soc = {})".format(self._current_soc),
                    tag="charge",
                    value="1"
                )
            )
            self._can_charge = True

    def disable_charge(self):
        """
        Stop discharging:
            set the capacity in the power source manager to 0 to mark it as unavailable
        """
        if not self._can_charge:
            # raise an exception if there's an attempt to stop discharging if it isn't actually discharging
            raise LpdmBatteryNotDischarging()
        elif self._power_level != 0:
            raise Exception("Can't disable charge while there is a load on the device.")

        self._logger.debug(
            self.build_message(
                message="Disable charge (soc = {})".format(self._current_soc),
                tag="charge",
                value="0"
            )
        )
        self._can_charge = False

    def start_charging(self):
        """
        Start charging the battery:
            calculate the max charge rate (W)
            set the capacity to 0
            add the load to the power source manager
        """
        if self._can_charge and not self._can_discharge:
            self._logger.info(
                self.build_message(
                    message="charge at soc {}".format(self._current_soc),
                    tag="charge",
                    value="1"
                )
            )
            # set the load to the charge rate
            # negative because energy is flowing into the device
            # self._power_level = -self.charge_rate()
            # set the power source manager capacity for the device
            # self.power_source_manager.set_capacity(self._device_id, 0.0)
            self._is_charging = True
            self.power_source_manager.add_load(self.charge_rate())
        else:
            raise Exception("battery is not able to charge, check parameters")

    def stop_charging(self):
        """stop the battery from charging"""
        if self.is_charging():
            # update the charge sum total
            self.sum_charge_kwh()
            self._logger.info(
                self.build_message(
                    message="charge",
                    tag="charge",
                    value="0"
                )
            )
            self._is_charging = False
            self.power_source_manager.remove_load(self.charge_rate())

    def shutdown(self):
        """Shutdown the battery"""
        # update the state of charge first
        self.update_state_of_charge()
        # stop all activity
        self.stop_charging()
        # self.stop_discharging()
        self.disable_discharge()

    def process_events(self):
        """Process any events that need to be processed"""
        remove_items = []
        for event in self._events:
            if event.ttie <= self._time:
                if event.value == "battery_status":
                    # self.update_status()
                    self.power_source_manager.optimize_load()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)

    def schedule_next_events(self):
        """Set up any events that needs to be processed in the future"""
        items = filter(lambda e: e.value == "battery_status", self._events)
        if len(items) == 0:
            self.set_next_battery_update_event()

    def set_next_battery_update_event(self):
        "If the battery is on update its state of charge every X number of seconds"
        new_event = LpdmEvent(self._time + self._check_soc_rate, "battery_status")
        # check if the event is already there
        found_items = filter(lambda d: d.ttie == new_event.ttie and d.value == "battery_status", self._events)
        if len(found_items) == 0:
            self._events.append(new_event)

    def sum_charge_kwh(self):
        """Keep a running total of the energy used for charging"""
        time_diff = self._time - self._last_charge_update_time
        power_level = self.charge_rate() if self._is_charging else 0
        if time_diff > 0 and power_level > 0:
            self._sum_charge_kwh += power_level * (time_diff / 3600.0)
        self._last_charge_update_time = self._time

    def write_calcs(self):
        PowerSource.write_calcs(self)
        self._logger.info(self.build_message(
            message="sum charge_kwh",
            tag="sum_charge_kwh",
            value=self._sum_charge_kwh / 1000.0
        ))
