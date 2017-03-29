

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
import logging
from lpdm_exception import LpdmMissingPowerSourceManager, LpdmBatteryDischargeWhileCharging, \
        LpdmBatteryNotDischarging, LpdmBatteryAlreadyDischarging, LpdmBatteryCannotDischarge, \
        LpdmBatteryChargeWhileDischarging, LpdmBatteryAlreadyCharging

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
        self._price = config.get("price", 0.0)

        self.power_source_manager = None

        self._load = 0.0
        self._current_capacity = None
        self._battery_on_time = None
        self._last_update_time = self._time
        self._charge_start_time = None
        self._can_charge = False
        self._is_charging = False
        self._can_discharge = False
        self._events = []

    def init(self):
        """no need to do any initialization for the battery"""
        self.update_status()
        self.schedule_next_events()

    def set_event_list(self, events):
        """Set the event list to one that has been passed in"""
        self._events = events

    def set_power_source_manager(self, psm):
        """Set the power source manager"""
        self.power_source_manager = psm

    def get_load(self):
        """Get the current load on the battery"""
        return self._load

    def set_load(self, new_load):
        """Set the load of the battery"""
        if new_load > 0:
            if not self._can_discharge:
                raise LpdmBatteryCannotDischarge()
        elif new_load < 0:
            raise Exception("Battery will set its own load when recharging")
        if new_load != self._load:
            self._load = new_load
            self._logger.info(
                self.build_message(
                    message="Set load to {}".format(self._load),
                    tag="power",
                    value=self._load
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
        self._load += new_load

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
        """
        Update the status of the battery:
            * Ok to discharge?
            * Ok to charge?
            * Neither
            * Discharging?
            * Charging?
        """
        if self.power_source_manager is None:
            raise LpdmMissingPowerSourceManager()

        # update the charge on the device
        self.update_state_of_charge()

        if self.is_discharging():
            # if battery is discharging
            # if self.power_source_manager.total_load() - self._load > 0:
                # is there other load besides from this device?
            if self.power_source_manager.output_capacity() > 0.70 and self._current_soc < 0.65:
                # stop discharging and do nothing
                self.disable_discharge()
            elif self._current_soc < self._min_soc:
                # stop discharging and start charging
                self.disable_discharge()
                self.enable_charge()
                self.start_charging()
            # else:
                # # stop discharging if there is no other load on the system
                # self.disable_discharge()
        elif self.is_charging():
            # battery is charging
            if self._current_soc >= self._max_soc \
            or (self.power_source_manager.output_capacity() < 0.3 and self._current_soc > 0.65):
                # stop discharging dn do nothing
                self.stop_charging()
                self.disable_charge()
                if not self._can_discharge and self.power_source_manager.output_capacity() < 0.3 and self._current_soc > 0.65:
                    # start to discharge the battery
                    self.enable_discharge()
        else:
            # Neither - not charging and not discharging (load == 0)
            # if self.power_source_manager.total_load() > 0 \
            if not self._can_discharge and self.power_source_manager.output_capacity() < 0.3 and self._current_soc > 0.65:
                # start to discharge the battery
                self.enable_discharge()

    def max_charge_rate(self):
        """Max rate that the battery can charge (W)"""
        return self._max_charge_rate

    def charge_rate(self):
        "The actual charge rate (W)"
        return self._max_charge_rate * self._roundtrip_eff

    def is_discharging(self):
        """Is the battery discharging?"""
        return self._can_discharge and self._load > 0

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
            if self.is_charging():
                self._current_soc = (
                    (self._capacity * self._current_soc)
                    + (self.charge_rate() * (self._time - self._last_update_time) / 3600.0)
                ) / (self._capacity)
            elif self._can_discharge and self._load > 0:
                self._current_soc = (
                    (self._capacity * self._current_soc)
                    - (self._load * (self._time - self._last_update_time) / 3600.0)
                ) / (self._capacity)

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
        elif self._load != 00:
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
                    message="charge",
                    tag="charge",
                    value="1"
                )
            )
            # set the load to the charge rate
            # negative because energy is flowing into the device
            # self._load = -self.charge_rate()
            # set the power source manager capacity for the device
            # self.power_source_manager.set_capacity(self._device_id, 0.0)
            self._is_charging = True
            self.power_source_manager.add_load(self.charge_rate())
        else:
            raise Exception("battery is not able to charge, check parameters")

    def stop_charging(self):
        """stop the battery from charging"""
        if self.is_charging():
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
            if event["time"] <= self._time:
                if event["operation"] == "battery_status":
                    # self.update_status()
                    self.power_source_manager.optimize_load()
                    remove_items.append(event)

        # remove the processed events from the list
        for event in remove_items:
            self._events.remove(event)
        return

    def schedule_next_events(self):
        """Set up any events that needs to be processed in the future"""
        items = filter(lambda e: e["operation"] == "battery_status", self._events)
        if len(items) == 0:
            self.set_next_battery_update_event()

    def set_next_battery_update_event(self):
        "If the battery is on update its state of charge every X number of seconds"
        self._events.append({"time": self._time + self._check_soc_rate, "operation": "battery_status"})

