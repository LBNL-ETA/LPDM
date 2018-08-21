import unittest
from Build.Objects.notebook_personal_computer import NotebookPersonalComputer
import logging

class NotebookPersonalComputerBatteryTest(unittest.TestCase):

    #@unittest.skip
    def test_charge_internal_battery_with_various_soc_and_price(self):

        charging_state_of_charge_intercept = 1.0
        charging_price_intercept = 0.5
        discharging_state_of_charge_intercept = 1.2
        discharging_price_intercept = 0.6
        nominal_voltage = 12
        nominal_current = 2
        capacity_in_ah = 41.4 / nominal_voltage # [Ah]

        internal_battery = NotebookPersonalComputer.Battery(charging_state_of_charge_intercept,
                                                            charging_price_intercept,
                                                            discharging_state_of_charge_intercept,
                                                            discharging_price_intercept,
                                                            nominal_voltage, nominal_current,
                                                            capacity_in_ah)

        internal_battery.state_of_charge = 0.2
        price_1 = 0.1
        actual_desired_power_level_1 = internal_battery.calculate_desired_power_level(price_1)
        expected_desired_power_level_1 = 24
        self.assertEqual(actual_desired_power_level_1, expected_desired_power_level_1)

        price_2 = 0.2
        actual_desired_power_level_2 = internal_battery.calculate_desired_power_level(price_2)
        expected_desired_power_level_2 = 24
        self.assertEqual(actual_desired_power_level_2, expected_desired_power_level_2)

        price_3 = 0.3
        actual_desired_power_level_3 = internal_battery.calculate_desired_power_level(price_3)
        expected_desired_power_level_3 = 24
        self.assertEqual(actual_desired_power_level_3, expected_desired_power_level_3)

        price_4 = 0.4
        actual_desired_power_level_4 = internal_battery.calculate_desired_power_level(price_4)
        # Due to floating point division, charging_boundary_state_of_charge_for_given_price becomes
        # 1.99... instead of 2.0
        expected_desired_power_level_4 = 0
        self.assertEqual(actual_desired_power_level_4, expected_desired_power_level_4)

        price_5 = 0.5
        actual_desired_power_level_5 = internal_battery.calculate_desired_power_level(price_5)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_5 = -24
        self.assertEqual(actual_desired_power_level_5, expected_desired_power_level_5)

        price_6 = 0.6
        actual_desired_power_level_6 = internal_battery.calculate_desired_power_level(price_6)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_6 = -24
        self.assertEqual(actual_desired_power_level_6, expected_desired_power_level_6)

        price_6 = 0.7
        actual_desired_power_level_6 = internal_battery.calculate_desired_power_level(price_6)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_6 = -24
        self.assertEqual(actual_desired_power_level_6, expected_desired_power_level_6)

        internal_battery.state_of_charge = 0.5
        price_7 = 0.1
        actual_desired_power_level_7 = internal_battery.calculate_desired_power_level(price_7)
        expected_desired_power_level_7 = 24
        self.assertEqual(actual_desired_power_level_7, expected_desired_power_level_7)

        price_8 = 0.2
        actual_desired_power_level_8 = internal_battery.calculate_desired_power_level(price_8)
        expected_desired_power_level_8 = 24
        self.assertEqual(actual_desired_power_level_8, expected_desired_power_level_8)

        price_9 = 0.3
        actual_desired_power_level_9 = internal_battery.calculate_desired_power_level(price_9)
        expected_desired_power_level_9 = 0
        self.assertEqual(actual_desired_power_level_9, expected_desired_power_level_9)

        price_10 = 0.4
        actual_desired_power_level_10 = internal_battery.calculate_desired_power_level(price_10)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_10 = -24
        self.assertEqual(actual_desired_power_level_10, expected_desired_power_level_10)

        price_11 = 0.5
        actual_desired_power_level_11 = internal_battery.calculate_desired_power_level(price_11)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_11 = -24
        self.assertEqual(actual_desired_power_level_11, expected_desired_power_level_11)

        price_12 = 0.6
        actual_desired_power_level_12 = internal_battery.calculate_desired_power_level(price_12)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_12 = -24
        self.assertEqual(actual_desired_power_level_12, expected_desired_power_level_12)

        price_13 = 0.7
        actual_desired_power_level_13 = internal_battery.calculate_desired_power_level(price_13)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_13 = -24
        self.assertEqual(actual_desired_power_level_13, expected_desired_power_level_13)

        internal_battery.state_of_charge = 0.8
        price_14 = 0.1
        actual_desired_power_level_14 = internal_battery.calculate_desired_power_level(price_14)
        expected_desired_power_level_14 = 24
        self.assertEqual(actual_desired_power_level_14, expected_desired_power_level_14)

        price_15 = 0.2
        actual_desired_power_level_15 = internal_battery.calculate_desired_power_level(price_15)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_15 = -24
        self.assertEqual(actual_desired_power_level_15, expected_desired_power_level_15)

        price_16 = 0.3
        actual_desired_power_level_16 = internal_battery.calculate_desired_power_level(price_16)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_16 = -24
        self.assertEqual(actual_desired_power_level_16, expected_desired_power_level_16)

        price_17 = 0.4
        actual_desired_power_level_17 = internal_battery.calculate_desired_power_level(price_17)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_17 = -24
        self.assertEqual(actual_desired_power_level_17, expected_desired_power_level_17)

        price_18 = 0.5
        actual_desired_power_level_18 = internal_battery.calculate_desired_power_level(price_18)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_18 = -24
        self.assertEqual(actual_desired_power_level_18, expected_desired_power_level_18)

        price_19 = 0.6
        actual_desired_power_level_19 = internal_battery.calculate_desired_power_level(price_19)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_19 = -24
        self.assertEqual(actual_desired_power_level_19, expected_desired_power_level_19)

        price_20 = 0.7
        actual_desired_power_level_20 = internal_battery.calculate_desired_power_level(price_20)
        # Discharge to supply power to the computer instead of making computer get power from
        # Grid Controller:
        expected_desired_power_level_20 = -24
        self.assertEqual(actual_desired_power_level_20, expected_desired_power_level_20)

    #@unittest.skip
    def test_charging_boundary_state_of_charge(self):

        charging_state_of_charge_intercept = 0.6
        charging_price_intercept = 0.2
        discharging_state_of_charge_intercept = 1.0
        discharging_price_intercept = 0.4
        nominal_voltage = 12
        nominal_current = 2
        capacity_in_ah = 41.4 / nominal_voltage
        price = 0.1

        internal_battery = NotebookPersonalComputer.Battery(charging_state_of_charge_intercept,
                                                            charging_price_intercept,
                                                            discharging_state_of_charge_intercept,
                                                            discharging_price_intercept,
                                                            nominal_voltage, nominal_current,
                                                            capacity_in_ah)

        actual_state_of_charge = \
                              internal_battery._calculate_charging_boundary_state_of_charge(price)

        expected_state_of_charge = 0.3

        self.assertEqual(actual_state_of_charge, expected_state_of_charge)

    #@unittest.skip
    def test_discharge(self):

        charging_state_of_charge_intercept = 1.0
        charging_price_intercept = 0.5
        discharging_state_of_charge_intercept = 1.2
        discharging_price_intercept = 0.6
        nominal_voltage = 12
        nominal_current = 2
        capacity_in_ah = 41.4 / nominal_voltage

        internal_battery = NotebookPersonalComputer.Battery(charging_state_of_charge_intercept,
                                                            charging_price_intercept,
                                                            discharging_state_of_charge_intercept,
                                                            discharging_price_intercept,
                                                            nominal_voltage, nominal_current,
                                                            capacity_in_ah)

        internal_battery.state_of_charge = 0.9

        actual_power_that_cannot_be_supplied = internal_battery.discharge(12 * 5 * 0.1)
        actual_state_of_charge = internal_battery.state_of_charge

        expected_state_of_charge = 0.7551

        self.assertEqual(actual_power_that_cannot_be_supplied, 0.0)
        self.assertAlmostEqual(actual_state_of_charge, expected_state_of_charge, delta = 0.001)
