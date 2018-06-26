from abc import ABCMeta, abstractmethod

from Build.Objects.grid_equipment import GridEquipment
from Build.Objects.utility_meter import UtilityMeter
from Build.Simulation_Operation.message import Message, MessageType, MessageRedirect
from Build.Simulation_Operation.event import Event
from Build.Simulation_Operation.support import nonzero_power
from Build.Objects.device import Device
from Build.Objects.converter.efficiency_curve import EfficiencyCurve

from Build.Simulation_Operation.support import SECONDS_IN_DAY

class Converter(GridEquipment):
    def __init__(self, device_id, supervisor, time=0, msg_latency=0, device_input=None, device_output=None,
                 efficiency_curve=None, capacity=None):
        super().__init__(device_id, "Converter", supervisor, msg_latency=msg_latency)
        self._logger.info(
            self.build_log_notation(
                message="build the converter device {}".format(device_id),
                tag=None,
                value=None
            )
        )
        if type(device_input) is str:
            self._device_input_id = device_input
        elif type(device_input) is dict:
            self._device_input_id = device_input["device_id"]
        else:
            raise Exception("{} device input is invalid".format(device_id))
        if type(device_output) is str:
            self._device_output_id = device_output
        elif type(device_output) is dict:
            self._device_output_id = device_output["device_id"]
        else:
            raise Exception("{} device input is invalid".format(device_id))
        # self._device_input = device_input
        # self._device_output = device_output
        self._efficiency_curve_input = efficiency_curve
        self._capacity = capacity
        self._has_utm = False
        self._load = 0.0
        self._load_loss = 0.0
        self._efficiency_curve = None
        self.build_efficiency_curve()

        self._converter_loss_power = 0.0
        self._converter_loss_energy = 0.0
        self._time_last_loss_calc = self._time
    
    def build_efficiency_curve(self):
        "Build the efficiency curve object"
        self._efficiency_curve = EfficiencyCurve(self._efficiency_curve_input, self._capacity)
    
    def register_device(self, device, device_id, value, wire=None):
        self._logger.info(
            self.build_log_notation(
                message="register device {}, {}, {}, {}".format(device, device_id, value, wire),
                tag=None,
                value=None
            )
        )
        super().register_device(device, device_id, value, wire)
        if isinstance(device, UtilityMeter):
            if self._has_utm:
                raise Exception("A Utility has already been connected to Converter {}".format(self._device_id))
            else:
                self._has_utm = True
    
    def is_input_device(self, device_id):
        "Determines if the device_id is the input device"
        return device_id == self._device_input_id
        # return device_id == self._device_input["device_id"]
    
    def has_utm(self):
        return self._has_utm
    
    def set_power_flow(self, sender_id, receiver_id, load):
        """Keeps track of the power flowing through the converter.

        A positive load indicates power flowing from the input device to the output device,
        this should be stored in _power_in and power should be added.
        A negative load indicates power flowing from the output device to the input device,
        this should be stores in _power_out.

        Parameters
        ----------
        sender_id: str
            The device_id of the message sender. If load is positive
        receiver_id: str
            The device_id of the receiver of the message
        load: float
            The power flowing through the converter
        """
        if load > 0:
            # power is flowing from the input device to the output device
            self.set_power_in(load)
            self._logger.info(
                self.build_log_notation(
                    message="power flow",
                    tag="power_in",
                    value=load
                )
            )
        elif load < 0:
            # power is flowing from the output device to the input device
            self.set_power_out(abs(load))
            self._logger.info(
                self.build_log_notation(
                    message="power flow",
                    tag="power_out",
                    value=abs(load)
                )
            )
        else:
            # load is 0, no power flowing through the converter
            if self._power_in:
                self._logger.info(
                    self.build_log_notation(
                        message="power flow",
                        tag="power_in",
                        value=load
                    )
                )
                self.set_power_in(load)
            elif self._power_out:
                self.set_power_out(load)
                self._logger.info(
                    self.build_log_notation(
                        message="power flow",
                        tag="power_out",
                        value=abs(load)
                    )
                )
        return
    
    def get_receiving_device(self, sender_device_id):
        "get the device_id of the receiving device to pass the message"
        if sender_device_id == self._device_input_id:
            return self._device_output_id
        elif sender_device_id == self._device_output_id:
            return self._device_input_id
        else:
            raise Exception("Unknown device_id {}".format(sender_device_id))
        # if sender_device_id == self._device_input["device_id"]:
        #     return self._device_output
        # elif sender_device_id == self._device_output["device_id"]:
        #     return self._device_input
        # else:
        #     raise Exception("Unknown device_id {}".format(sender_device_id))

    def process_power_message(self, message):
        "Process a power message"
        self._logger.info(
            self.build_log_notation(
                message="POWER message from {}".format(message.sender_id),
                tag="power_msg_in",
                value=message.value
        ))
        receiver_id = self.get_receiving_device(message.sender_id)
        self.set_power_flow(message.sender_id, receiver_id, message.value)
        self.send_power_message(receiver_id, message.value)
        # self.set_power_flow(message.sender_id, receiver["device_id"], message.value)
        # self.send_power_message(receiver["device_id"], message.value)

    def process_price_message(self, message):
        # pass on price messages from output -> inputs
        self._logger.info(
            self.build_log_notation(
                message="Receive PRICE message from {}".format(message.sender_id),
                tag="price_msg",
                value=message.value
            )
        )
        receiver_id = self.get_receiving_device(message.sender_id)
        self.send_price_message(receiver_id, message.value)
        # self.send_price_message(receiver["device_id"], message.value)

    def process_request_message(self, message):
        # send request message from an input to the output device
        self._logger.info(
            self.build_log_notation(
                message="Receive REQUEST message from {}".format(message.sender_id),
                tag="request_msg",
                value=message.value
            )
        )
        receiver_id = self.get_receiving_device(message.sender_id)
        # request extra to account for the converter loss
        converter_loss = self._efficiency_curve.get_converter_loss(message.value)
        # reequest extra to account for wire loss
        wire_loss = self.calculate_wire_loss(receiver_id, message.value)
        self.send_request_message(receiver_id, message.value + converter_loss + wire_loss)
        # wire_loss = self.calculate_wire_loss(receiver["device_id"], message.value)
        # self.send_request_message(receiver["device_id"], message.value + converter_loss + wire_loss)

    def process_allocate_message(self, message):
        self._logger.info(
            self.build_log_notation(
                message="Receive ALLOCATE message from {}".format(message.sender_id),
                tag="allocate_msg",
                value=message.value
            )
        )
        receiver_id = self.get_receiving_device(message.sender_id)
        self.send_allocate_message(receiver_id, message.value)
        # self.send_allocate_message(receiver["device_id"], message.value)

    def send_allocate_message(self, target_id, allocate_amt):
        self._logger.info(
            self.build_log_notation(
                message="ALLOCATE to {}".format(target_id),
                tag="allocate_msg",
                value=allocate_amt
            )
        )
        target_device = self._connected_devices[target_id]
        if target_device:
            # self._allocated[target_id] = -allocate_amt
            target_device.receive_message(Message(self._time, self._device_id, MessageType.ALLOCATE, allocate_amt))
        else:
            raise Exception('Invalid device_id found ({})'.format(target_id))
    
    ##
    # This method is called when the EUD is requesting to use power from a GC.
    # @param target_id the recipient of the request message (must be a GC)
    # @param request_amt the amount of power this EUD is requesting to receive (must be positive)

    def send_request_message(self, target_id, request_amt):
        # if request_amt < 0:
        #     raise ValueError("EUD cannot request to distribute power")
        if target_id in self._connected_devices and isinstance(self._connected_devices[target_id], GridEquipment):  # cannot request from non-GC's
            target_device = self._connected_devices[target_id]
        else:
            raise ValueError("invalid target to request")
        self._logger.info(self.build_log_notation(message="REQUEST to {}".format(target_id),
                                                  tag="request_msg", value=request_amt))
        target_device.receive_message(Message(self._time, self._device_id, MessageType.REQUEST, request_amt))

    def send_power_message(self, target_id, power_amt):
        target_device = self._connected_devices[target_id]
        # add extra to account for the converter loss if power is flowing
        if power_amt:
            # if power_amt > 0:
            #     converter_loss = self._efficiency_curve.get_converter_loss(power_amt)
            # else:
            #     converter_loss = self._efficiency_curve.get_converter_loss_source(power_amt)
            converter_loss = self._efficiency_curve.get_converter_loss(power_amt)
            power_amt += converter_loss
            self.update_converter_loss(converter_loss)
        # add extra to account for wire loss
        wire_loss = self.calculate_wire_loss(target_id, power_amt)
        power_amt += wire_loss
        self.update_wire_loss_in(target_id, abs(wire_loss))

        target_device.receive_message(Message(self._time, self._device_id, MessageType.POWER, power_amt))
        self._logger.info(self.build_log_notation(message="POWER to {}".format(target_id),
                                                  tag="power_msg", value=power_amt))

    def update_converter_loss(self, converter_loss_power):
        "Update the converter loss rate for power flowing into the device"
        previous = self._converter_loss_power
        # if previous and converter_loss_power:
        self.sum_converter_loss(previous)
        self._converter_loss_power = converter_loss_power

    def sum_converter_loss(self, converter_loss_power):
        time_diff = self._time - self._time_last_loss_calc
        if time_diff > 0:
            # Wh = W*s*(h/3600s)
            converter_loss_energy = converter_loss_power * (time_diff / 3600.0)
            self._converter_loss_energy += converter_loss_energy
            self._logger.info(
                self.build_log_notation(
                    message="Calculate converter loss, dt = {} h, rate = {} W, energy = {} Wh".format( \
                        time_diff / 3600.0, converter_loss_power, converter_loss_energy),
                    tag="converter_loss",
                    value=converter_loss_energy
            ))
        self._time_last_loss_calc = self._time

    def last_wire_loss_calc(self):
        for (device_id, wire_loss_rate) in self._wire_loss_info_in.items():
            if wire_loss_rate:
                self.update_wire_loss_in(device_id, wire_loss_rate)
        self.update_converter_loss(0.0)

    def device_specific_calcs(self):
        pass
    
    def calculate_power_loss(self):
        "Calculate the power loss based on the current capacity"
        pass

    def send_price_message(self, target_id, price):
        if target_id in self._connected_devices:
            target = self._connected_devices[target_id]
        else:
            raise ValueError("This GC is connected to no such device")
        self._logger.info(self.build_log_notation(message="PRICE to {}".format(target_id),
                                                  tag="price_msg", value=price))
        target.receive_message(Message(self._time, self._device_id, MessageType.PRICE, price))


