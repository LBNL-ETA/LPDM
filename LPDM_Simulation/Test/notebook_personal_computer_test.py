import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor
from Build.Simulation_Operation.message import Message
from Build.Simulation_Operation.message import MessageType
import logging
from dateutil import parser

class NotebookPersonalComputerTest(unittest.TestCase):

    def setUp(self):
        self._logger = logging.getLogger("test")
        self.device_id = 1 # Note: Assuming it is an integer not UUID.
        self.supervisor = Supervisor()
        self.notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor)

    #@unittest.skip
    def test_start_up(self):

        self.notebook_personal_computer.start_up()

        # Note: Since there is not assertNotRaises, if this test doesn't cause any error, it is considered to be success.

    #@unittest.skip
    def test_shut_down(self):

        self.notebook_personal_computer.shut_down()

        self.assertEqual(self.notebook_personal_computer._in_operation, False)

    #@unittest.skip
    def test_charge_internal_battery(self):

        max_operating_power = 12 * 5
        received_power = 12 * 9.8 # 9.8 - 5 [Ah] is used for charging battery
        battery_capacity = 48
        state_of_charge_before = 0.5

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power)
        notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_state_of_charge = 0.6

        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_charge_internal_battery_when_with_more_supply(self):

        max_operating_power = 12 * 5
        received_power = 12 * 10 # Only maximum of 9.8 - 5 [Ah] can be used for charging battery
        battery_capacity = 48
        state_of_charge_before = 0.9

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power)
        notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_state_of_charge = 1.0

        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_charge_internal_battery_when_soc_and_price_are_low_case_1(self):

        max_operating_power = 12 * 5
        # Considers the chart where price is in x axis and state of charge in y axis.
        charging_boundary_state_of_charge = 1.0
        charging_boundary_price = 0.6
        discharging_boundary_state_of_charge = 1.2
        discharging_boundary_price = 0.8
        nominal_voltage = 12
        nominal_current = 2
        capacity = 41.4
        battery_capacity = 48
        state_of_charge_before = 0.5

        time = parser.parse("2018-07-01 16:00:00")
        sender_id = "gc_1"
        message_type = MessageType.PRICE

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                        max_operating_power = max_operating_power,
                                        charging_boundary_state_of_charge = charging_boundary_state_of_charge,
                                        charging_boundary_price = charging_boundary_price,
                                        discharging_boundary_state_of_charge = discharging_boundary_state_of_charge,
                                        discharging_boundary_price = discharging_boundary_price,
                                        nominal_voltage = nominal_voltage,
                                        nominal_current = nominal_current,
                                        capacity = capacity)

        notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # notebook_personal_computer.start_up()
        # notebook_personal_computer.on()

        value_1 = 0.1
        message_1 = Message(time, sender_id, message_type, value_1, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_1)
        actual_desired_power_level_1 = notebook_personal_computer.calculate_desired_power_level()
        expected_desired_power_level_1 = 24
        self.assertEqual(actual_desired_power_level_1, expected_desired_power_level_1)

    #@unittest.skip
    def test_charge_internal_battery_when_soc_and_price_are_low_case_2(self):

        max_operating_power = 12 * 5
        # Considers the chart where price is in x axis and state of charge in y axis.
        charging_boundary_state_of_charge = 1.0
        charging_boundary_price = 0.6
        discharging_boundary_state_of_charge = 1.2
        discharging_boundary_price = 0.8
        nominal_voltage = 12
        nominal_current = 2
        capacity = 41.4
        battery_capacity = 48
        state_of_charge_before = 0.5

        time = parser.parse("2018-07-01 16:00:00")
        sender_id = "gc_1"
        message_type = MessageType.PRICE

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                        max_operating_power = max_operating_power,
                                        charging_boundary_state_of_charge = charging_boundary_state_of_charge,
                                        charging_boundary_price = charging_boundary_price,
                                        discharging_boundary_state_of_charge = discharging_boundary_state_of_charge,
                                        discharging_boundary_price = discharging_boundary_price,
                                        nominal_voltage = nominal_voltage,
                                        nominal_current = nominal_current,
                                        capacity = capacity)

        notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # notebook_personal_computer.start_up()
        # notebook_personal_computer.on()

        value_2 = 0.2
        message_2 = Message(time, sender_id, message_type, value_2, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_2)
        actual_desired_power_level_2 = notebook_personal_computer.calculate_desired_power_level()
        expected_desired_power_level_2 = 24
        self.assertEqual(actual_desired_power_level_2, expected_desired_power_level_2)

    #@unittest.skip
    def test_calculate_charging_boundary_state_of_charge(self):

        charging_boundary_state_of_charge = 0.6
        charging_boundary_price = 0.2
        discharging_boundary_state_of_charge = 1.0
        discharging_boundary_price = 0.4
        nominal_voltage = 12
        nominal_current = 2
        capacity = 41.4
        price = 0.1

        internal_battery = NotebookPersonalComputer.Battery(charging_boundary_state_of_charge,
                                                            charging_boundary_price,
                                                            discharging_boundary_state_of_charge,
                                                            discharging_boundary_price,
                                                            nominal_voltage, nominal_current,
                                                            capacity)

        actual_state_of_charge = \
                              internal_battery._calculate_charging_boundary_state_of_charge(price)

        expected_state_of_charge = 0.3

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)
