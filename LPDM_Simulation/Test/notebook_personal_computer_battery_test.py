import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
import logging

class NotebookPersonalComputerBatteryTest(unittest.TestCase):

    #@unittest.skip
    def test_charge_internal_battery_when_soc_and_price_are_low_case_1(self):

        charging_state_of_charge_intercept = 0.6
        charging_price_intercept = 0.2
        discharging_state_of_charge_intercept = 1.0
        discharging_price_intercept = 0.4
        nominal_voltage = 12
        nominal_current = 2
        capacity = 41.4

        internal_battery = NotebookPersonalComputer.Battery(charging_state_of_charge_intercept,
                                                            charging_price_intercept,
                                                            discharging_state_of_charge_intercept,
                                                            discharging_price_intercept,
                                                            nominal_voltage, nominal_current,
                                                            capacity)

        price_1 = 0.1
        actual_desired_power_level_1 = internal_battery.calculate_desired_power_level(price_1)
        expected_desired_power_level_1 = 24
        self.assertEqual(actual_desired_power_level_1, expected_desired_power_level_1)

        price_2 = 0.2
        actual_desired_power_level_2 = internal_battery.calculate_desired_power_level(price_2)
        expected_desired_power_level_2 = 24
        self.assertEqual(actual_desired_power_level_2, expected_desired_power_level_2)

    #@unittest.skip
    def test_charging_boundary_state_of_charge(self):

        charging_state_of_charge_intercept = 0.6
        charging_price_intercept = 0.2
        discharging_state_of_charge_intercept = 1.0
        discharging_price_intercept = 0.4
        nominal_voltage = 12
        nominal_current = 2
        capacity = 41.4
        price = 0.1

        internal_battery = NotebookPersonalComputer.Battery(charging_state_of_charge_intercept,
                                                            charging_price_intercept,
                                                            discharging_state_of_charge_intercept,
                                                            discharging_price_intercept,
                                                            nominal_voltage, nominal_current,
                                                            capacity)

        actual_state_of_charge = \
                              internal_battery._calculate_charging_boundary_state_of_charge(price)

        expected_state_of_charge = 0.3

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)
