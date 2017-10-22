
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
        # Dictionary of devices and how much this EUD has been allocated by those devices. All values must be positive
        self._allocated = {}
        # Dictionary of devices and how much power this EUD is currently receiving from those entities
        self._loads_in = {}
        # EUD receives price messages from GC's only. For now, assume it will always update price.
        self._price = 0
        self._in_operation = False
        # flag to determine whether we use request-allocate model or immediate power.
        self._power_direct = power_direct

    # ___________________ BASIC FUNCTIONS ________________

    ##
    # Turns on the EUD, seeking to update to its desired power level. Previous state functions such as price
    # are maintained.
    # TODO: Rename this to Start Up. Registers this device with all of its connected devices.
    def turn_on(self):
        self._logger.info(self.build_log_notation(
            message="start up {}".format(self._device_id),
            tag="start_up",
            value=1
        ))
        # Set power levels to update the power charge calculations.
        self._in_operation = True
        self.begin_internal_operation()
        self.modulate_power()
        # self.set_power_in(0) this is a problem if things do not happen in the right order.
        # self.set_power_out(0)

    # TODO: Rename this to Shut Down. Removes this device from the active grid.
    ##
    # Turns off the EUD. Reduces all power consumption to 0 and informs all connected grid controllers
    # of this change.
    def turn_off(self):
        self._logger.info(self.build_log_notation(
            message="shut down {}".format(self._device_id),
            tag="shut_down",
            value=0
        ))

        gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
        for gc in gcs:
            self.send_power_message(gc, 0)
            self.change_load_in(gc, 0)
        self.set_power_in(0)
        self.set_power_out(0)
        self.end_internal_operation()
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
            self._loads_in[sender_id] = -new_power
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

        target_device.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    def change_load_in(self, sender_id, new_load):
        prev_load = self._loads_in.get(sender_id, 0)
        self.recalc_sum_power(prev_load, new_load)
        self._loads_in[sender_id] = new_load
    ##
    # Method to be called once it needs to recalculate its internal power usage.
    # To be called after price, power level, or allocate has changed.
    # This function will change the EUD's power level to the desired level.
    # This function is compatible with this EUD being associated with multiple grid controllers.

    # TODO: This as a prototype for the GC modulate power function (shifting loads from more to less expensive).
    # TODO: GC modulate power function will have a 'timeout', where it can add an event to modulate power 10s later.
    def modulate_power(self):
        self.update_state()  # make sure we are updated before calculating any desired power
        desired_power_level = self.calculate_desired_power_level()
        if desired_power_level > 0:
            remaining = desired_power_level  # how much we have left to get (ignoring what we are getting already)
            total_power_taken = 0

            power_sources = []  # list of gcs we will get power from.
            gcs = [key for key in self._connected_devices.keys() if key.startswith("gc")]
            # TODO: Take in order of prices from the sources.
            # TODO: Move power direct into the top level for this decision.
            # gcs_by_price = sorted(gcs, key=lambda d: self._gc_prices.get(d, 1000.0))
            for device in self._allocated.keys():
                if device in gcs:
                    # take all up to what we've been allocated.
                    take_power = min(remaining, self._allocated[device])
                    self.send_power_message(device, take_power)
                    self.change_load_in(device, take_power)
                    remaining -= take_power
                    total_power_taken += take_power
                    if take_power:
                        power_sources.append(device)
                    if remaining <= 0:
                        break

            # TODO: Make this dependent on prices instead. Request all from cheapest first. 
            if remaining > 0:
                num_gcs = len(gcs)
                if num_gcs:
                    for gc in gcs:
                        prev_load = self._loads_in.get(gc, 0)
                        extra_power = remaining / num_gcs # add a fractional value
                        if self._power_direct:
                            self.send_power_message(gc, prev_load + extra_power)
                            self.change_load_in(gc, prev_load + extra_power)
                            total_power_taken += extra_power
                        else:
                            self.send_request_message(gc, extra_power)
                        power_sources.append(gc)  # TODO: Decide if this is correct for both here?

            # clear the record with all GC's that we didn't get power from.
            for gc in gcs:
                if gc not in power_sources:
                    self.send_power_message(gc, 0)
                    self.change_load_in(gc, 0)

            self.respond_to_power(requested_power=desired_power_level, received_power=total_power_taken)

        ##
    # EUD specific processes to initiate when this device turns on
    @abstractmethod
    def begin_internal_operation(self):
        pass

    ##
    # Eud specific processes to initiate or terminate when this device turns off
    @abstractmethod
    def end_internal_operation(self):
        pass

    ##
    # Calculates EUD's desired power in to support its current internal state levels.
    # NOTE: EUD must be in_operation for this function to work.
    # @return the eud's desired power in

    @abstractmethod
    def calculate_desired_power_level(self):
        pass

    ##
    # How this EUD responds once it receives a given quantity of power after requesting a certain amount.
    # @param requested_power how much this device wanted to consume
    # @param received_power how much power this device immediately received
    @abstractmethod
    def respond_to_power(self, requested_power, received_power):
        pass

    ##
    # Call to update all the internal state functions of the EUD. Call this function before calling
    # calculate desired power level.
    @abstractmethod
    def update_state(self):
        pass

    @abstractmethod
    def device_specific_calcs(self):
        pass
