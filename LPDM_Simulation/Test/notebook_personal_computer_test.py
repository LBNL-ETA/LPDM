import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor
import logging

class NotebookPersonalComputerTest(unittest.TestCase):

    def setUp(self):
        self._logger = logging.getLogger("test")
        device_id = 1 # Note: Assuming it is an integer not UUID.
        supervisor = Supervisor()
        self.notebook_personal_computer = NotebookPersonalComputer(device_id, supervisor)

    def test_start_up(self):

        self.notebook_personal_computer.start_up()

        # Note: Since there is not assertNotRaises, if this test doesn't cause any error, it is considered to be success.

    def test_shut_down(self):

        self.notebook_personal_computer.shut_down()

        self.assertEqual(self.notebook_personal_computer._in_operation, False)
