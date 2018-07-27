import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
from Build.Simulation_Operation.supervisor import Supervisor
from Build.Objects.grid_controller import GridController
from Build.Objects.battery import Battery

class NotebookPersonalComputerIntegrationTest(unittest.TestCase):

    def test_simple_interation_with_grid_controller(self):

        supervisor = Supervisor()

        notebook_personal_computer_device_id = "notebook_personal_computer_1"
        notebook_personal_computer = NotebookPersonalComputer(notebook_personal_computer_device_id, supervisor)

        battery_id = "battery_1"
        battery_price_logic = 'moving_average' # According to the constructor of Battery class, 'hourly_preference' or 'moving_average'
        capacity = 1200.0 # in [Wh] though it is defined in [Ah] in related science and data sheet
        max_charge_rate = 120 # in [W], assuming it's 12[V] battery with 100 [Ah] capacity, rouchly lasting 10 hours, 10[A] maximum.
                              # Note: Charge rate varies depending on state of charge.
        max_discharge_rate = 120 # in [W], same value as above, simplifying for now.
        battery = Battery(battery_id, battery_price_logic, capacity, max_charge_rate, max_discharge_rate)

        grid_controller_device_id = "grid_controller_1"
        grid_controller_price_logic = 'marginal_price' # According to the constructor of GridController,
                                                       # 'weighted_average', 'marginal_price', 'marginal_price_b', or 'static_price'
        grid_controller = GridController(grid_controller_device_id, supervisor, battery = battery, price_logic = grid_controller_price_logic,
                                         connected_devices = [notebook_personal_computer])

        supervisor.register_device(notebook_personal_computer)
        supervisor.register_device(grid_controller)

        grid_controller.send_register_message("notebook_personal_computer_1", 1)
        grid_controller.build_device_list()
        grid_controller.send_power_message("notebook_personal_computer_1", 10)
        





