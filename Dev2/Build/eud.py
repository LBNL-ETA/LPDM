
########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""
    Implementation of a general EUD device, which requests and consumes certain amounts of power.
    For current simplicity, the EUD maintains up to one connection with a grid controller at a time
    and is connected to no other devices. Hence, its only messaging occurs with the Grid Controller
    it is connected to.
"""

from Build.device import Device
from Build.message import Message, MessageType
from abc import abstractmethod


class Eud(Device):

    def __init__(self, device_id, device_type, supervisor, time=0, msg_latency=0, power_direct=False,
                 schedule=None, connected_devices=None):
        super().__init__(device_id, device_type, supervisor, time=time, msg_latency=msg_latency, schedule=schedule,
                         connected_devices=connected_devices)
        # Dictionary of devices and how much the device has been allocated by those devices. All values must be positive
        self._allocated = {}
        self._price = 0  # EUD receives price messages from GC's only. For now, assume it will always update price.
        self._in_operation = False
        self._power_direct = power_direct  # flag to determine whether we use request-allocate model or immediate power.

    # ___________________ BASIC FUNCTIONS ________________

    ##
    # Turns on the EUD, seeking to update to its desired power level. Previous state functions such as price
    # are maintained.
    def turn_on(self):
        self._logger.info(self.build_log_notation(
            message="turn on {}".format(self._device_id),
            tag="turn_on",
            value=1
        ))

        # Set power levels to update the power charge calculations.
        self._in_operation = True
        self.modulate_power()
        # self.set_power_in(0) this is a problem if things do not happen in the right order.
        # self.set_power_out(0)

    ##
    # Turns off the EUD. Reduces all power consumption to 0 and informs all connected grid controllers
    # of this change.
    def turn_off(self):
        self._logger.info(self.build_log_notation(
            message="turn off {}".format(self._device_id),
            tag="turn_off",
            value=0
        ))

        gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
        for gc in gcs:
            self.send_power_message(gc, 0)
        self.set_power_in(0)
        self.set_power_out(0)
        self._in_operation = False

    ##
    # Sets the quantity of power that this EUD has been allocated to consume by a specific device

    # @param device_id the id of the device which has allocated the amount of power
    # @param allocate_amt the amount of power allocated for this device to consume. Must be positive.
    #
    def set_allocated(self, device_id, allocate_amt):
        if allocate_amt < 0:
            raise ValueError("EUD cannot allocate to provide power")
        else:
            self._allocated[device_id] = allocate_amt

    # ____________________MESSAGING FUNCTIONS___________________________
    ##
    # Method to be called when this EUD receives a power message. If there is an erroneous message suggesting
    # for the EUD to provide power, it immediately responds with a "0" price message.
    # @param sender_id the sender of the power message
    # @param new_power the new power value from the sender's perspective

    def process_power_message(self, sender_id, new_power):
        if new_power <= 0:
            self.set_power_in(-new_power)
            self.modulate_power()
        else:
            self.send_power_message(sender_id, 0)
            self._logger.info(self.build_log_notation("ignored positive power message from {}".format(sender_id)))

    ##
    # EUD's do not respond to request messages.
    def process_request_message(self, sender_id, request_amt):
        self._logger.info(self.build_log_notation("ignored request message from {}".format(sender_id)))

    ##
    # Method to be called after the EUD receives a price message from a grid controller, immediately updating its price.
    def process_price_message(self, sender_id, new_price):
        self._price = new_price  # EUD always updates its value to the price it receives.
        self.modulate_power()

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power.
    #
    # @param sender_id the device who has allocated to provide the given quantity
    # @param allocated_amt the amount that the sending device has allocated to receive from this EUD. Hence, this EUD
    # cannot respond unless the value is negative, since the EUD only consumes power.

    def process_allocate_message(self, sender_id, allocate_amt):
        if allocate_amt > 0:  # can not send power, so ignore this message
            self._logger.info(self.build_log_notation("ignored positive allocate message from {}".format(sender_id)))
        self.set_allocated(sender_id, -allocate_amt)  # records the amount this device has been allocate
        self.modulate_power()

    ##
    # This method is called when the EUD is requesting to use power from a GC.
    # @param target_id the recipient of the request message (must be a GC)
    # @param request_amt the amount of power this EUD is requesting to receive (must be positive)

    def send_request_message(self, target_id, request_amt):
        if request_amt < 0:
            raise ValueError("EUD cannot request to distribute power")
        if target_id in self._connected_devices.keys() and target_id.startswith("gc"):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        self._logger.info(self.build_log_notation(message="REQUEST to {}".format(target_id),
                                                  tag="request_msg", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    # This method is called when the EUD wishes to inform a grid controller that it is now consuming X watts of power.
    # @param target_id the recipient of the power message (must be a GC)
    # @param power_amt the value of the new load from this device's perspective.
    def send_power_message(self, target_id, power_amt):
        if power_amt < 0:
            raise ValueError("EUD cannot distribute power")
        if target_id in self._connected_devices.keys() and target_id.startswith("gc"):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        self._logger.info(self.build_log_notation(message="POWER to {}".format(target_id),
                                                  tag="power_msg", value=power_amt))

        self.recalc_sum_power(self._power_in, power_amt)
        target_device.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    ##
    # Method to be called once it needs to recalculate its internal power usage.
    # To be called after price, power level, or allocate has changed.
    # This function will change the EUD's power level to the desired level.

    # TODO: Make it so EUD's can reduce consumption if they are taking too much.
    # TODO: Fix infinite loop with message between grid controller and EUD here.
    def modulate_power(self):
        desired_power_level = self.calculate_desired_power_level()
        power_seek = desired_power_level - self._power_in
        remaining = power_seek  # how much we have left to get
        if power_seek:
            for gc in self._allocated.keys():  # take all up to what we've been allocated.
                take_power = min(remaining, self._allocated[gc])
                self.send_power_message(gc, take_power)
                remaining -= take_power
                if remaining <= 0:
                    break
            if remaining > 0:
                gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
                if len(gcs):
                    if gcs[0] not in self._allocated.keys():
                        if self._power_direct:
                            self.send_power_message(gcs[0], remaining)  # TODO: For now, assume 1 connected GC.
                        else:
                            self.send_request_message(gcs[0], remaining)
                else:
                    # TODO: self.low_power()?
                    self.turn_off()  # unable to receive power to support its operation.

    ##
    # Calculates EUD's desired power in to support its current internal state levels.
    # @return the eud's desired power in

    @abstractmethod
    def calculate_desired_power_level(self):
        pass

    def device_specific_calcs(self):
        pass
