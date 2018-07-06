import unittest
from Build.Objects.personal_computer import PersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor

class PersonalComputerTest(unittest.TestCase):

    def setUp(self):
        device_id = 1 # Note: Assuming it is an integer not UUID.
        supervisor = Supervisor()
        self.personal_computer = PersonalComputer(device_id, supervisor)

    def test_start_up(self):

        self.personal_computer.start_up()

        # Note: Since there is not assertNotRaises, if this test doesn't cause any error, it is considered to be success.
