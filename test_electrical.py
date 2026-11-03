import unittest
from electrical import calculate_dc


class TestCalculateDC(unittest.TestCase):
    def test_known_values(self):
        current_a, power_w = calculate_dc(12, 6)
        self.assertAlmostEqual(current_a, 2.0)
        self.assertAlmostEqual(power_w, 24.0)

    def test_zero_voltage(self):
        current_a, power_w = calculate_dc(0, 10)
        self.assertAlmostEqual(current_a, 0.0)
        self.assertAlmostEqual(power_w, 0.0)

    def test_zero_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_dc(12, 0)

    def test_negative_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_dc(12, -1)

    def test_voltage_must_be_finite(self):
        for voltage_v in (float("nan"), float("inf")):
            with self.subTest(voltage_v=voltage_v):
                with self.assertRaises(ValueError):
                    calculate_dc(voltage_v, 6)

    def test_resistance_must_be_finite(self):
        for resistance_ohm in (float("nan"), float("inf")):
            with self.subTest(resistance_ohm=resistance_ohm):
                with self.assertRaises(ValueError):
                    calculate_dc(12, resistance_ohm)


if __name__ == "__main__":
    unittest.main()