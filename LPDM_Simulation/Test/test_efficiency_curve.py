import unittest
from Build.Objects.converter.efficiency_curve import EfficiencyCurve

curve_data = [
    {"capacity": 0.1, "efficiency": 0.6},
    {"capacity": 0.2, "efficiency": 0.7},
    {"capacity": 0.3, "efficiency": 0.75},
    {"capacity": 0.4, "efficiency": 0.8},
    {"capacity": 0.5, "efficiency": 0.83},
    {"capacity": 0.6, "efficiency": 0.85},
    {"capacity": 0.7, "efficiency": 0.86},
    {"capacity": 0.75, "efficiency": 0.86},
    {"capacity": 0.8, "efficiency": 0.85},
    {"capacity": 0.9, "efficiency": 0.83},
    {"capacity": 1, "efficiency": 0.8}
]
max_capacity = 1000
efficiency_curve = EfficiencyCurve(curve_data, max_capacity)

class TestEfficiencyCurve(unittest.TestCase):
    def test_edge_beginning(self):
        "load 90/1000 below the first capacity 0.1"
        load = 90
        ef = curve_data[0]
        self.assertEqual(efficiency_curve.get_converter_loss(load), load - (ef["efficiency"] * load))

    def test_edge_end(self):
        "load 1000/1000 should use the last effiency value"
        load = 1000 
        ef = curve_data[-1]
        self.assertEqual(efficiency_curve.get_converter_loss(load), load - (ef["efficiency"] * load))

    def test_between(self):
        "load 150/1000 should use effiency value between 0.6 and 0.7 (0.65)"
        load = 150 
        self.assertAlmostEqual(efficiency_curve.get_converter_loss(load), load - (0.65 * load))
    
    def test_exact_capacity(self):
        "load percentage lands exactly on an efficency value e.g. 0.5"
        load = 500
        ef = curve_data[4]
        self.assertEqual(efficiency_curve.get_converter_loss(load), load - (ef["efficiency"] * load))

    def test_exact_capacity_negative(self):
        "negative load value should produce a negative loss value"
        load = -500
        ef = curve_data[4]
        self.assertEqual(efficiency_curve.get_converter_loss(load), load - (ef["efficiency"] * load))

if __name__ == '__main__':
    unittest.main()
