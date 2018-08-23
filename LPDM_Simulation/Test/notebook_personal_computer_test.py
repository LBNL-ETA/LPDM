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
        battery_capacity = 48 * 12 # [Wh]
        state_of_charge_before = 0.5

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power,
                                            capacity = battery_capacity)
        # notebook_personal_computer.internal_battery.capacity_in_ah = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_power_consumption_ratio = 1.0
        expected_state_of_charge = 0.6

        actual_power_consumption_ratio = notebook_personal_computer.power_consumption_ratio
        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_power_consumption_ratio, expected_power_consumption_ratio)
        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_charge_internal_battery_when_with_more_supply(self):

        max_operating_power = 12 * 5
        received_power = 12 * 10 # Only maximum of 9.8 - 5 [Ah] can be used for charging battery
        battery_capacity = 48 * 12 # [Wh]
        state_of_charge_before = 0.9

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power,
                                            capacity = battery_capacity)
        # notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_power_consumption_ratio = 1.0
        expected_state_of_charge = 1.0

        actual_power_consumption_ratio = notebook_personal_computer.power_consumption_ratio
        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_power_consumption_ratio, expected_power_consumption_ratio)
        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_keep_minimum_power_consumption(self):

        power_level_max = 1.0
        power_level_low = 0.2
        max_operating_power = 12 * 5
        received_power = 12 * 5 * 0.1 # less than max_operating_power * power_level_low
        battery_capacity = 48 * 12 # [Wh]
        state_of_charge_before = 0.9

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power,
                                            power_level_max = power_level_max,
                                            power_level_low = power_level_low,
                                            capacity = battery_capacity)
        # notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_power_consumption_ratio = 0.2
        # Discharge battery to compensate the lack of power:
        expected_state_of_charge = 0.8896

        actual_power_consumption_ratio = notebook_personal_computer.power_consumption_ratio
        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_power_consumption_ratio, expected_power_consumption_ratio)
        self.assertAlmostEqual(actual_state_of_charge, expected_state_of_charge, delta = 0.001)

    def test_power_consumption_relative_to_received_power(self):

        power_level_max = 1.0
        power_level_low = 0.2
        max_operating_power = 12 * 5
        received_power = 12 * 5 * 0.3 # more than max_operating_power * power_level_low
                                      # less than max_operating_power * power_level_max
        battery_capacity = 48 * 12 # [Wh]
        state_of_charge_before = 0.9

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                            max_operating_power = max_operating_power,
                                            power_level_max = power_level_max,
                                            power_level_low = power_level_low,
                                            capacity = battery_capacity)
        # notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_power_consumption_ratio = 0.3
        # Stays the same because received power is less than maximum operating power for computer:
        expected_state_of_charge = 0.9

        actual_power_consumption_ratio = notebook_personal_computer.power_consumption_ratio
        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge

        self.assertEqual(actual_power_consumption_ratio, expected_power_consumption_ratio)
        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_calculate_desired_power_level_when_medium_soc(self):

        max_operating_power = 12 * 5
        # Considers the chart where price is in x axis and state of charge in y axis.
        charging_state_of_charge_intercept = 1.0
        charging_price_intercept = 0.5
        discharging_state_of_charge_intercept = 1.2 # Actually, this value is an intercept to y-axis
        discharging_price_intercept = 0.6
        nominal_voltage = 12
        nominal_current = 2
        battery_capacity = 48 * 12 # [Wh]
        state_of_charge_before = 0.5

        time = parser.parse("2018-07-01 16:00:00")
        sender_id = "gc_1"
        message_type = MessageType.PRICE

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor,
                                        max_operating_power = max_operating_power,
                                        charging_state_of_charge_intercept = charging_state_of_charge_intercept,
                                        charging_price_intercept = charging_price_intercept,
                                        discharging_state_of_charge_intercept = discharging_state_of_charge_intercept,
                                        discharging_price_intercept = discharging_price_intercept,
                                        nominal_voltage = nominal_voltage,
                                        nominal_current = nominal_current,
                                        capacity = battery_capacity)

        # notebook_personal_computer.internal_battery.capacity = battery_capacity
        notebook_personal_computer.internal_battery.state_of_charge = state_of_charge_before

        # notebook_personal_computer.start_up()
        # notebook_personal_computer.on()

        price_1 = 0.1
        message_1 = Message(time, sender_id, message_type, price_1, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_1)
        actual_desired_power_level_1 = notebook_personal_computer.calculate_desired_power_level()
        expected_desired_power_level_1 = 84
        self.assertEqual(actual_desired_power_level_1, expected_desired_power_level_1)

        price_2 = 0.2
        message_2 = Message(time, sender_id, message_type, price_2, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_2)
        actual_desired_power_level_2 = notebook_personal_computer.calculate_desired_power_level()
        expected_desired_power_level_2 = 36
        self.assertEqual(actual_desired_power_level_2, expected_desired_power_level_2)

        price_3 = 0.3
        message_3 = Message(time, sender_id, message_type, price_3, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_3)
        actual_desired_power_level_3 = notebook_personal_computer.calculate_desired_power_level()
        expected_desired_power_level_3 = 12
        self.assertEqual(actual_desired_power_level_3, expected_desired_power_level_3)

        price_4 = 0.4
        message_4 = Message(time, sender_id, message_type, price_4, extra_info=None, redirect=None)
        # This message contains price and this method assign the price:
        notebook_personal_computer.process_price_message(message_4)
        actual_desired_power_level_4 = notebook_personal_computer.calculate_desired_power_level()
        # Since notebook personal computer doesn't send power to Grid Controller,
        # if the calculated desired_power_level becomes less than 0, it is set to 0.
        expected_desired_power_level_4 = 0
        self.assertEqual(actual_desired_power_level_4, expected_desired_power_level_4)
