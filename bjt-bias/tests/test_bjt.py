import unittest

from bjt import FIELD_ORDER, BiasError, BiasInput, parse_input


DEFAULT_RAW = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "2200",
    "re": "470",
    "beta": "150",
    "vbe": "0.7",
}


def raw_with(**overrides):
    raw = dict(DEFAULT_RAW)
    for key, value in overrides.items():
        if value is None:
            raw.pop(key, None)
        else:
            raw[key] = value
    return raw


class TestParseInput(unittest.TestCase):
    def test_known_happy_case(self):
        parsed = parse_input(DEFAULT_RAW)
        self.assertEqual(parsed, BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 150.0, 0.7))
        self.assertAlmostEqual(parsed.vcc_v, 12.0)
        self.assertAlmostEqual(parsed.r1_ohm, 47000.0)
        self.assertAlmostEqual(parsed.r2_ohm, 10000.0)
        self.assertAlmostEqual(parsed.rc_ohm, 2200.0)
        self.assertAlmostEqual(parsed.re_ohm, 470.0)
        self.assertAlmostEqual(parsed.beta, 150.0)
        self.assertAlmostEqual(parsed.vbe_v, 0.7)

    def test_missing_field_is_rejected(self):
        with self.assertRaises(BiasError) as context:
            parse_input(raw_with(r2=None))
        self.assertTrue(context.exception.errors)

    def test_empty_string_is_missing(self):
        for text in ("", "   "):
            with self.subTest(text=text):
                with self.assertRaises(BiasError):
                    parse_input(raw_with(r1=text))

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(BiasError):
            parse_input(raw_with(rc="abc"))

    def test_nan_inf_rejected(self):
        bad_values = ("nan", "inf", "-inf")
        for field in ("vcc", "re"):
            for value in bad_values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(BiasError):
                        parse_input(raw_with(**{field: value}))

    def test_nonpositive_values_rejected(self):
        bad_values = (
            {"vcc": "0"},
            {"vcc": "-5"},
            {"r1": "0"},
            {"re": "-1"},
            {"beta": "0"},
        )
        for overrides in bad_values:
            with self.subTest(overrides=overrides):
                with self.assertRaises(BiasError):
                    parse_input(raw_with(**overrides))

    def test_vbe_must_be_less_than_vcc(self):
        for vbe in ("-0.1", "12"):
            with self.subTest(vbe=vbe):
                with self.assertRaises(BiasError):
                    parse_input(raw_with(vbe=vbe))


if __name__ == "__main__":
    unittest.main()
