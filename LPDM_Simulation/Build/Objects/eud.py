
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
    Implementation of a general EUD device, which only consumes power based on its internal state.
"""

from abc import abstractmethod

from Build.Objects.grid_equipment import GridEquipment
from Build.Simulation_Operation.message import Message, MessageType
from Build.Simulation_Operation.event import Event
from Build.Simulation_Operation.support import nonzero_power
from Build.Objects.device import Device


class Eud(Device):

    def __init__(self, device_id, device_type, supervisor, total_runtime, time=0, msg_latency=0, power_direct=False,
                 modulation_interval=600, schedule=None, multiday=0, connected_devices=None):
        super().__init__(device_id, device_type, supervisor, time=time, msg_latency=msg_latency, schedule=schedule,
                         multiday=multiday, total_runtime=total_runtime, connected_devices=connected_devices)
        # Dictionary of devices and how much this EUD has been allocated by those devices. All values must be positive
        self._allocated = {}
        # Dictionary of devices and how much power this EUD is currently receiving from those entities
        self._loads_in = {}
        # EUD receives price messages from GC's only. For now, assume it will always update price.
        self._price = 0
        self._in_operation = False
        # flag to determine whether we use request-allocate model or immediate power.
        self._power_direct = power_direct
        # Record when we get price messages. Avoid responding to flurries of messages unless significantly different.
        self._last_price_message_time = 0
        # Reevaluate this device's power and its sources at a given interval
        self.setup_modulation_schedule(modulation_interval, total_runtime)

        # Time in seconds within which this EUD will not readjust its power levels in response to new price messages
        # unless the price change is larger than PRICE_RECALIBRATION_INTERVAL (defined below).
        self.power_recalibration_interval = 5

        # Minimum price change which will cause this EUD to reevaluate its power levels if it occurs within the
        # recalibration interval
        self.price_recalibration_interval = 0.02

    # ___________________ BASIC FUNCTIONS ________________

    ##
    # Turns on the EUD, seeking to update to its desired power level. Previous state functions such as price
    # are maintained. If EUD is already on, does not do anything.
    def start_up(self):
        if not self._in_operation:
            # TODO: self.engage()
            # Set power levels to update the power charge calculations.
            self._in_operation = True
            self.begin_internal_operation()
            self.modulate_power()

    ##
    # Turns off the EUD. Reduces all power consumption to 0 and informs all connected grid controllers
    # of this change.
    def shut_down(self):
        self._logger.info(self.build_log_notation(
            message="shut down {}".format(self._device_id),
            tag="shut_down",
            value=0
        ))

        gcs = [device_id for device_id in self._connected_devices.keys() if isinstance(self._connected_devices[device_id], GridEquipment)]
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

    ##
    # The EUD will modulate its power every 10 minutes.
    def setup_modulation_schedule(self, modulation_interval, total_runtime):
        if modulation_interval <= 0:
            return
        curr_time = self._time + modulation_interval  # start 1 interval in
        while curr_time < total_runtime:
            self.add_event(Event(self.modulate_power), curr_time)
            curr_time += modulation_interval

    # ____________________MESSAGING FUNCTIONS___________________________
    ##
    # Method to be called when this EUD receives a power message. If there is an erroneous message suggesting
    # for the EUD to provide power, it immediately responds with a "0" price message.
    # @param sender_id the sender of the power message
    # @param new_power the new power value from the sender's perspective

    def process_power_message(self, message):
        if message.value <= 0:
            self.set_power_in(-message.value)
            self._loads_in[message.sender_id] = -message.value
            self.respond_to_power(-message.value)
        else:
            self.send_power_message(message.sender_id, 0)
            self._logger.info(self.build_log_notation("ignored positive power message from {}".format(message.sender_id)))

    ##
    # EUD's do not respond to request messages.
    def process_request_message(self, message):
        self._logger.info(self.build_log_notation("ignored request message from {}".format(message.sender_id)))

    ##
    # Method to be called after the EUD receives a price message from a grid controller, immediately updating its price.
    def process_price_message(self, message):
        prev_price = self._price
        price_delta = abs(message.value - prev_price)
        self._price = message.value  # EUD always updates its value to the price it receives.
        self._logger.info(
            self.build_log_notation(
                message="ignored request message from {}".format(message.sender_id),
                tag="price",
                value=message.value
        ))

        if self._time - self._last_price_message_time >= self.power_recalibration_interval or \
           price_delta > self.price_recalibration_interval:
            # Only modulate power if we haven't received a message recently or new price is very different
            self.modulate_power()
        self._last_price_message_time = self._time

    ##
    # Method to be called once device has allocated to provide a given quantity of power to another device,
    # or to receive a given quantity of power.
    #
    # @param sender_id the device who has allocated to provide the given quantity
    # @param allocated_amt the amount that the sending device has allocated to receive from this EUD. Hence, this EUD
    # cannot respond unless the value is negative, since the EUD only consumes power.

    def process_allocate_message(self, message):
        if message.value < 0:  # can not send power, so ignore this message
            self._logger.info(self.build_log_notation("ignored negative allocate message from {}".format(message.sender_id)))
        # TODO: subtract out the wire loss?
        self.set_allocated(message.sender_id, message.value)  # records the amount this device has been allocated
        self.modulate_power()

    ##
    # This method is called when the EUD is requesting to use power from a GC.
    # @param target_id the recipient of the request message (must be a GC)
    # @param request_amt the amount of power this EUD is requesting to receive (must be positive)

    def send_request_message(self, target_id, request_amt):
        if request_amt < 0:
            raise ValueError("EUD cannot request to distribute power")
        if target_id in self._connected_devices and isinstance(self._connected_devices[target_id], GridEquipment):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        # if there's a wire attached add it onto the request amount
        wire_loss = self.calculate_wire_loss(target_id, request_amt)
        request_amt += wire_loss
        self._logger.info(self.build_log_notation(message="REQUEST to {}".format(target_id),
                                                  tag="request_out", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    # This method is called when the EUD wishes to inform a grid controller that it is now consuming X watts of power.
    # @param target_id the recipient of the power message (must be a GC)
    # @param power_amt the value of the new load from this device's perspective.
    def send_power_message(self, target_id, power_amt):
        if power_amt < 0:
            raise ValueError("EUD cannot distribute power")
        if target_id in self._connected_devices and isinstance(self._connected_devices[target_id], GridEquipment):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")        
        # if there's a wire attached add it onto the request amount
        wire_loss = self.calculate_wire_loss(target_id, power_amt)
        power_amt += wire_loss
        self.update_wire_loss_in(target_id, abs(wire_loss))

        self._logger.info(self.build_log_notation(message="POWER to {}".format(target_id),
                                                  tag="power_out", value=power_amt))

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

        # self._logger.info(self.build_log_notation(message="desired power level", tag="desired_power", value=desired_power_level))
        gcs = [device_id for device_id in self._connected_devices.keys() if isinstance(self._connected_devices[device_id], GridEquipment)]

        if desired_power_level == 0:
            for gc in gcs:
                if nonzero_power(self._loads_in.get(gc, 0)):
                    self.send_power_message(gc, 0)
                    self.change_load_in(gc, 0)

        elif desired_power_level > 0:
            # how much we have left to get (ignoring what we are getting already)
            remaining = desired_power_level
            total_power_taken = 0

            power_sources = []  # list of gcs we will get power from.

            # TODO: Take in order of prices from the sources.
            # TODO: Move power direct into the top level for this decision.
            # gcs_by_price = sorted(gcs, key=lambda d: self._gc_prices.get(d, 1000.0))
            for device in self._allocated.keys():
                if device in gcs:
                    # take all up to what we've been allocated.
                    take_power = min(remaining, self._allocated[device])
                    if nonzero_power(self._loads_in.get(device, 0) - take_power):
                        # We currently aren't taking the correct amt, send a power message
                        self.send_power_message(device, take_power)
                        self.change_load_in(device, take_power)
                        remaining -= take_power
                        total_power_taken += take_power
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
                            # self.update_wire_loss_in(gc, wire_loss)
                            total_power_taken += extra_power
                        else:
                            self.send_request_message(gc, prev_load + extra_power)
                        power_sources.append(gc)  # TODO: Decide if this is correct for both here?

            # clear the record with all GC's that we didn't get power from.
            for gc in gcs:
                if gc not in power_sources:
                    self.send_power_message(gc, 0)
                    self.change_load_in(gc, 0)

            self.respond_to_power(total_power_taken)

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
    # @param received_power how much power this device immediately received (must be positive value)
    @abstractmethod
    def respond_to_power(self, received_power):
        pass

    ##
    # Call to update all the internal state functions of the EUD. Call this function before calling
    # calculate desired power level.
    @abstractmethod
    def update_state(self):
        pass

    ##
    # All device specific end-of-simulation calculations are EUD-specific.
    @abstractmethod
    def device_specific_calcs(self):
        pass

    def last_wire_loss_calc(self):
        for (device_id, wire_loss_rate) in self._wire_loss_info_in.items():
            if wire_loss_rate:
                self.update_wire_loss_in(device_id, wire_loss_rate)
