

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

from tug_devices.grid_controller import GridController
from tug_devices.eud import Eud
from tug_devices.diesel_generator import DieselGenerator

class Messenger:
    def __init__(self, config = None):
        self._subscribers_to_power = []
        self._subscribers_to_time = []
        self._subscribers_to_price = []
        self._subscribers_to_ttie = []
        self._device_notifications_through_gc = config["device_notifications_through_gc"] if type(config) is dict and "device_notifications_through_gc" in config.keys() else False

    def subscribeToPowerChanges(self, device):
        self._subscribers_to_power.append(device)

    def subscribeToPriceChanges(self, device):
        self._subscribers_to_price.append(device)

    def subscribeToTimeChanges(self, device):
        self._subscribers_to_time.append(device)

    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        """
            Messenger receives a price change, notify all subscribers to the price change.
            If the _device_notifications_through_gc flag has been set, then let the grid controller send the notifications to the devices,
            otherwise send the notifications to the devices themselves
        """
        for device in self._subscribers_to_power:
            if target_device_id == 'all' or target_device_id == device.deviceID():
                device.onPowerChange(source_device_id, target_device_id, time, new_power)

    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        """
            Messenger receives a price change, notify all subscribers to the price change.
            If the _device_notifications_through_gc flag has been set, then let the grid controller send the notifications to the devices,
            otherwise send the notifications to the devices themselves
        """
        for device in self._subscribers_to_power:
            if target_device_id == 'all' or target_device_id == device.deviceID():
                device.onPriceChange(source_device_id, target_device_id, time, new_price)

    def onNewTTIE(self, source_device_id, target_device_id, new_ttie):
        # time.sleep(0.12) # When time.sleep(0.12), one day will run in one minute (1d = 1m)
        return

    def changePower(self, source_device_id, target_device_id, time, new_power):
        for device in self._subscribers_to_power:
            device.onPowerChange(source_device_id, target_device_id, time, new_power)

    def changePrice(self, source_device_id, target_device_id, time, new_price):
        for device in self._subscribers_to_price:
            device.onPriceChange(source_device_id, target_device_id, time, new_price)

    def changeTime(self, new_time):
        for device in self._subscribers_to_time:
            device.onTimeChange(new_time)
