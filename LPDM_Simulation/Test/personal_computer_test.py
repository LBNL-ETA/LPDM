import unittest
from Build.Objects.personal_computer import PersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor
import logging

class PersonalComputerTest(unittest.TestCase):

    def setUp(self):
        self._logger = logging.getLogger("test")
        device_id = 1 # Note: Assuming it is an integer not UUID.
        supervisor = Supervisor()
        self.personal_computer = PersonalComputer(device_id, supervisor)

    def test_start_up(self):

        self._logger.info("In PersonalComputerTest#test_start_up")

        self.personal_computer.start_up()

        # Note: Since there is not assertNotRaises, if this test doesn't cause any error, it is considered to be success.

    def test_shut_down(self):

        self.personal_computer.shut_down()

        self.assertEqual(self.personal_computer._in_operation, False)
