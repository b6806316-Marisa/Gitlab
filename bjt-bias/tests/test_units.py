import unittest

from units import RESISTANCE_UNITS, VOLTAGE_UNITS, UnitError, to_si, unit_label


class TestToSi(unittest.TestCase):
    def test_voltage_units(self):
        self.assertEqual(to_si("12", "v", "voltage"), "12.0")
        self.assertEqual(to_si("12", "mv", "voltage"), "0.012")

    def test_millivolts_to_volts(self):
        self.assertAlmostEqual(float(to_si("12000", "mv", "voltage")), 12.0)

    def test_resistance_units(self):
        self.assertEqual(to_si("100", "kohm", "resistance"), "100000.0")
        self.assertEqual(to_si("470", "ohm", "resistance"), "470.0")
        self.assertEqual(to_si("1", "mohm", "resistance"), "1000000.0")

    def test_blank_is_unchanged(self):
        for text in ("", "   "):
            with self.subTest(text=text):
                self.assertEqual(to_si(text, "kohm", "resistance").strip(), "")

    def test_non_numeric_is_unchanged(self):
        self.assertEqual(to_si("abc", "kohm", "resistance"), "abc")

    def test_unknown_unit_raises_error(self):
        with self.assertRaises(UnitError):
            to_si("12", "furlong", "voltage")
        with self.assertRaises(UnitError):
            to_si("100", "furlong", "resistance")

    def test_negative_and_decimal_values(self):
        self.assertAlmostEqual(float(to_si("-2.5", "v", "voltage")), -2.5)
        self.assertAlmostEqual(float(to_si("2.2", "kohm", "resistance")), 2200.0)


class TestUnitLabel(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(unit_label("voltage", "v"), "V")
        self.assertEqual(unit_label("voltage", "mv"), "mV")
        self.assertEqual(unit_label("resistance", "kohm"), "kΩ")
        self.assertEqual(unit_label("resistance", "ohm"), "Ω")

    def test_unit_lists(self):
        self.assertIn(("v", "V"), VOLTAGE_UNITS)
        self.assertIn(("kohm", "kΩ"), RESISTANCE_UNITS)


if __name__ == "__main__":
    unittest.main()
