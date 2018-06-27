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


from Build.Simulation_Operation.message import Message, MessageType
from Build.Simulation_Operation.support import SECONDS_IN_DAY
from Build.Simulation_Operation.event import Event
from Build.Objects.device import Device
from Build.Objects.grid_equipment import GridEquipment
from Build.Objects.device_type import PowerGiver


class PV(GridEquipment, PowerGiver):

    def __init__(self, device_id, supervisor, power_profile, peak_power, time=0, msg_latency=0,
                 schedule=None, connected_devices=None, total_runtime=SECONDS_IN_DAY):

        super().__init__(device_id=device_id, device_type="pv", supervisor=supervisor,
                         time=time, msg_latency=msg_latency, schedule=schedule, connected_devices=connected_devices)
        self.setup_power_schedule(power_profile, peak_power, total_runtime)

    ##
    # Sets up the power generation schedule for this PV. Takes input of a daily power generation schedule.
    # @param power_profile list of (time, power_proportion) pairs for the PV profile
    # @param peak_power peak power generated from PV unit, i.e. solar capacity
    # @param total_runtime total number of days to run PV unit (usually simulation duration) 
    def setup_power_schedule(self, power_profile, peak_power, total_runtime):
        # Check if power level list spans multiple days, or is single day repeat
        multiday_input = False
        for time, power_proportion in power_profile:
            if time > 86400:
                multiday_input = True
                break
        if multiday_input: # multiple day power level list (i.e. PVWatts)
            for time, power_proportion in power_profile:
                power_event = Event(self.update_power_status, peak_power, power_proportion)
                self.add_event(power_event, time)
        else: # single day repeated power level list
            curr_day = int(self._time / SECONDS_IN_DAY)  # Current day in seconds
            while curr_day < total_runtime:
                for time, power_proportion in power_profile:
                    power_event = Event(self.update_power_status, peak_power, power_proportion)
                    self.add_event(power_event, time + curr_day)
                curr_day += SECONDS_IN_DAY

    ##
    # Sets up the power generation schedule for this PV. Takes input of a daily power generation schedule.
    # Power
    # TODO: assumes total_runtime is in days, and schedule is at most one day long, and schedule is
    # TODO: in percentage of peak power. Make this more robust?
#     def setup_power_schedule(self, power_profile, peak_power, total_runtime):
#         curr_day = int(self._time / SECONDS_IN_DAY)  # Current day in seconds. Starts at the PV's initial time.
#         while curr_day < total_runtime:
#             for time, power_proportion in power_profile:
#                 power_event = Event(self.update_power_status, peak_power, power_proportion)
#                 if time < curr_day:
#                     # LPDM PV profile
#                     self.add_event(power_event, time + curr_day)
#                 else:
#                     # PVWatts profile
#                     self.add_event(power_event, time)
#             curr_day += SECONDS_IN_DAY

    ##
    # Changes the amount of power that this device is producing and
    # If this PV is connected to multiple devices, it evenly distributes its load amongst them.
    def update_power_status(self, peak_power, power_percent):
        num_connections = len(self._connected_devices)
        power_amt = (peak_power * power_percent)
        if power_amt != self._power_out:
            for device_id in self._connected_devices.keys():
                send_power = power_amt / num_connections
                self.send_power_message(device_id, -send_power)
            self.set_power_out(power_amt)

    ##
    # This PV will provide the power it , informing another device of the quantity by
    def send_power_message(self, target_id, power_amt):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This PV is connected to no such device")
        # add in additional wire loss
        # if wire_loss is non-zero, then there's a wire attached
        wire_loss = self.calculate_wire_loss(target_id, power_amt)
        if wire_loss:
            if power_amt:
                # if power_amt is non-zero, add in additional wire loss
                power_amt += wire_loss
                self.update_wire_loss_out(target_id, abs(wire_loss))
            else:
                # power_amt is zero so no wire loss
                self.update_wire_loss_out(target_id, 0)
        self._logger.info(self.build_log_notation(message="POWER to {}".format(target_id),
                                                  tag="power_out", value=power_amt))
        target.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))

    ##
    # PV does not respond to external power messages
    #
    # @param sender_id the sender of the message providing or receiving the new power
    # @param new_power the value of power flow from sender's perspective
    # positive if sender is receiving, negative if sender is providing.
    def process_power_message(self, message):
        raise ValueError("PV should not receive power information")

    ##
    # PV does not respond to price information
    #
    # @param sender_id the sender of the message informing of the new price
    # @param new_price the new price value
    def process_price_message(self, message):
        pass

    ##
    # PV does not respond to request information
    #
    # @param request_amt the amount the sending device is requesting to receive (positive) or send (negative)
    def process_request_message(self, message):
        pass

    ##
    # PV does not respond to allocate messages
    #
    # @param allocated_amt the amount allocated from perspective of message sender.
    # Positive indicates this device is allocated to take, negative indicates this device is allocated to provide.
    # device (negative).
    def process_allocate_message(self, message):
        pass

    ##
    # PV does not calculate any new usage information besides sum power out
    def device_specific_calcs(self):
        pass

    def last_wire_loss_calc(self):
        pass
