

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

from device.simulated.utility_meter import UtilityMeter
from device.base.power_source_buyer import PowerSourceBuyer
from lpdm_event import LpdmBuyPowerPriceEvent, LpdmBuyMaxPowerEvent, LpdmBuyPowerEvent

class UtilityMeterBuyer(UtilityMeter, PowerSourceBuyer):
    """
    Implementation of a utility meter that will buy back power from the grid controller.
    """
    def __init__(self, config):
        UtilityMeter.__init__(self, config)
        # max amount of power the utility meter can buy
        self._max_buy_capacity = config.get("max_buy_capacity", 2000.0)
        # current amount of power bought
        self._current_power_bought = 0.0
        # keep track of the start/stop times for power bought
        self._last_buy_update_time = 0.0
        # keep a running total of power bought
        self._sum_kwh_buy = 0.0
        # price threshold: the price at which to start buying power from the grid
        self._price_buy_threshold = config.get("price_buy_threshold", 0.10)

    def init(self):
        """INitialize a power buyer"""
        # broadast the new power buy threshold
        self.broadcast_new_buy_price(self._price_buy_threshold)
        self.broadcast_new_max_buy_capacity(self._max_buy_capacity)
        UtilityMeter.init(self)

    def broadcast_new_buy_price(self, new_price):
        """Tell the grid controller what the price threshold is for purchasing back power"""
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new buy price",
                    tag="broadcast_buy_price",
                    value=new_price
                )
            )
            self._broadcast_callback(
                LpdmBuyPowerPriceEvent(self._device_id, self._grid_controller_id, self._time, new_price)
            )
        else:
            raise Exception("broadcast callback has not been set for this device!")
        return

    def broadcast_new_max_buy_capacity(self, value):
        """Tell the grid controller what the max amount of power the device can handle"""
        if callable(self._broadcast_callback):
            self._logger.debug(
                self.build_message(
                    message="Broadcast new max buy capacity",
                    tag="max_buy_capacity",
                    value=value
                )
            )
            self._broadcast_callback(
                LpdmBuyMaxPowerEvent(self._device_id, self._grid_controller_id, self._time, value)
            )
        else:
            raise Exception("broadcast callback has not been set for this device!")
        return

    def process_supervisor_event(self, the_event):
        """override the base class event to handle the buy back events"""
        self._time = the_event.time
        if isinstance(the_event, LpdmBuyPowerEvent):
            # power source is being notified that it can begin purchasing power
            if the_event.target_device_id == self._device_id:
                self._logger.debug(
                    self.build_message(message="buy power event received {}".format(the_event), tag="buy_power_received", value=1)
                )
                self.buy_power(the_event)
        else:
            UtilityMeter.process_supervisor_event(self, the_event)

    def buy_power(self, the_event):
        """Power purchase has been granted"""
        # update the total power bought
        self.sum_kwh_power_bought()
        self.set_power_bought(the_event.value)

    def set_power_bought(self, value):
        if value != self._current_power_bought:
            self._current_power_bought = value
            self._logger.debug(self.build_message(
                message="buy_power",
                tag="buy_power",
                value=value
            ))

    def sum_kwh_power_bought(self):
        """Keep a running total of the energy bought by the device"""
        if not self._time is None and not self._last_buy_update_time is None:
            time_diff = self._time - self._last_buy_update_time
            if time_diff > 0 and self._current_power_bought > 0:
                self._sum_kwh_buy += self._current_power_bought * (time_diff / 3600.0)
            self._last_buy_update_time = self._time

    def finish(self):
        self.sum_kwh_power_bought()
        self.write_calcs()

    def write_calcs(self):
        """override the base class implementation to write the power bought total to the db"""
        # perform the base class write_calss method first
        self._logger.info(self.build_message(
            message="sum kwh_buy",
            tag="sum_kwh_buy",
            value=self._sum_kwh_buy / 1000.0
        ))
