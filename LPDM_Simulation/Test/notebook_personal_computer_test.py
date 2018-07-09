import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor
import logging

class NotebookPersonalComputerTest(unittest.TestCase):

    def setUp(self):
        self._logger = logging.getLogger("test")
        self.device_id = 1 # Note: Assuming it is an integer not UUID.
        self.supervisor = Supervisor()
        self.notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor)

    def test_start_up(self):

        self.notebook_personal_computer.start_up()

        # Note: Since there is not assertNotRaises, if this test doesn't cause any error, it is considered to be success.

    def test_shut_down(self):

        self.notebook_personal_computer.shut_down()

        self.assertEqual(self.notebook_personal_computer._in_operation, False)

    def test_charge_battery(self):

        operating_power = 12 * 5
        received_power = 12 * 9.8 # 9.8 - 5 [Ah] is used for charging battery
        battery_capacity = 48
        state_of_charge_before = 0.5

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor, operating_power = operating_power)
        notebook_personal_computer.internal_battery.set_capacity(battery_capacity)
        notebook_personal_computer.internal_battery.set_stat_of_charge(state_of_charge_before)

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_state_of_charge = 0.6

        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge()

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    def test_charge_battery_when_with_more_supply(self):

        operating_power = 12 * 5
        received_power = 12 * 10 # Only maximum of 9.8 - 5 [Ah] can be used for charging battery
        battery_capacity = 48
        state_of_charge_before = 0.9

        notebook_personal_computer = NotebookPersonalComputer(self.device_id, self.supervisor, operating_power = operating_power)
        notebook_personal_computer.internal_battery.set_capacity(battery_capacity)
        notebook_personal_computer.internal_battery.set_stat_of_charge(state_of_charge_before)

        # Note: This acts more like private method but tested in unit test of this class:
        notebook_personal_computer.respond_to_power(received_power)

        expected_state_of_charge = 1.0

        actual_state_of_charge = notebook_personal_computer.internal_battery.state_of_charge()

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)
