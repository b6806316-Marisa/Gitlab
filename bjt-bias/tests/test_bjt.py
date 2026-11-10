import math
import unittest

from bjt import (
    FIELD_ORDER,
    BiasError,
    BiasInput,
    BiasResult,
    ComparisonRow,
    VCE_SAT_V,
    VCE_NEAR_V,
    classify,
    compare,
    parse_input,
    solve_nodal,
    solve_thevenin,
)


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

    def test_blank_field_says_required(self):
        with self.assertRaises(BiasError) as context:
            parse_input(raw_with(r1=""))
        message = " ".join(context.exception.errors)
        self.assertIn("กรุณาระบุค่า R1", message)
        self.assertNotIn("มากกว่าศูนย์", message)

    def test_non_finite_number_says_invalid_number(self):
        for text in ("nan", "inf"):
            with self.subTest(text=text):
                with self.assertRaises(BiasError) as context:
                    parse_input(raw_with(vcc=text))
                self.assertIn("VCC ต้องเป็นตัวเลขที่ถูกต้อง", " ".join(context.exception.errors))

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

class TestSolveThevenin(unittest.TestCase):
    def test_known_active_case(self):
        b = BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 150.0, 0.7)
        r = solve_thevenin(b)
        self.assertAlmostEqual(r.ib_a, 1.77397243587898e-05, delta=1e-12)
        self.assertAlmostEqual(r.ic_a, 0.0026609586538184696, delta=1e-9)
        self.assertAlmostEqual(r.ie_a, 0.0026786983781772597, delta=1e-9)
        self.assertAlmostEqual(r.vce_v, 4.886902723856055, delta=1e-6)
        self.assertAlmostEqual(r.vb_v, 1.958988237743312, delta=1e-6)
        self.assertAlmostEqual(r.ve_v, 1.2589882377433121, delta=1e-6)
        self.assertAlmostEqual(r.vc_v, 6.145890961599367, delta=1e-6)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, ())

    def test_cutoff_returns_zero_currents(self):
        b = BiasInput(12.0, 47000.0, 1000.0, 2200.0, 470.0, 150.0, 0.7)
        r = solve_thevenin(b)
        self.assertEqual(r.ib_a, 0.0)
        self.assertEqual(r.ic_a, 0.0)
        self.assertEqual(r.ie_a, 0.0)
        self.assertEqual(r.ve_v, 0.0)
        self.assertAlmostEqual(r.vce_v, 12.0)
        self.assertAlmostEqual(r.vb_v, 0.25)
        self.assertAlmostEqual(r.vc_v, 12.0)
        self.assertEqual(r.region, "cutoff")
        self.assertTrue(len(r.warnings) >= 1)

    def test_saturation_is_flagged_not_clamped(self):
        b = BiasInput(12.0, 10000.0, 10000.0, 10000.0, 100.0, 150.0, 0.7)
        r = solve_thevenin(b)
        self.assertLess(r.vce_v, 0.2)
        self.assertEqual(r.region, "saturation")
        self.assertTrue(len(r.warnings) >= 1)
        expected_vce = b.vcc_v - r.ic_a * b.rc_ohm - r.ie_a * b.re_ohm
        self.assertAlmostEqual(r.vce_v, expected_vce, delta=1e-9)

    def test_beta_extremes_are_finite(self):
        b1 = BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 1.0, 0.7)
        r1 = solve_thevenin(b1)
        for x in (r1.ib_a, r1.ic_a, r1.ie_a, r1.vce_v, r1.vb_v, r1.ve_v, r1.vc_v):
            self.assertTrue(math.isfinite(x))
        self.assertEqual(r1.region, "active")
        b2 = BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 1e6, 0.7)
        r2 = solve_thevenin(b2)
        for x in (r2.ib_a, r2.ic_a, r2.ie_a, r2.vce_v, r2.vb_v, r2.ve_v, r2.vc_v):
            self.assertTrue(math.isfinite(x))
        self.assertEqual(r2.region, "active")

    def test_classify_boundaries(self):
        self.assertEqual(classify(0.19), "saturation")
        self.assertEqual(classify(0.2), "saturation")
        self.assertEqual(classify(0.21), "active")
        self.assertEqual(classify(0.49), "active")
        self.assertEqual(classify(0.5), "active")
        self.assertEqual(classify(-1.0), "saturation")

class TestSolveNodal(unittest.TestCase):
    def test_nodal_agrees_with_thevenin(self):
        cases = [
            (12.0, 47000.0, 10000.0, 2200.0, 470.0, 150.0, 0.7),
            (9.0, 10000.0, 4700.0, 1000.0, 220.0, 100.0, 0.6),
            (5.0, 22000.0, 4700.0, 1200.0, 330.0, 200.0, 0.65),
            (12.0, 47000.0, 10000.0, 2200.0, 470.0, 1.0, 0.7),
            (12.0, 47000.0, 10000.0, 2200.0, 470.0, 1e6, 0.7),
            (12.0, 47000.0, 1000.0, 2200.0, 470.0, 150.0, 0.7),  # cutoff
        ]
        for case in cases:
            with self.subTest(case=case):
                b = BiasInput(*case)
                t = solve_thevenin(b)
                n = solve_nodal(b)
                self.assertEqual(t.region, n.region)
                for name in ("ib_a", "ic_a", "ie_a", "vce_v", "vb_v", "ve_v", "vc_v"):
                    tv = getattr(t, name)
                    nv = getattr(n, name)
                    if abs(tv) < 1e-12 and abs(nv) < 1e-12:
                        continue
                    denom = max(abs(tv), 1e-12)
                    self.assertLessEqual(abs(tv - nv) / denom, 1e-9, name)

    def test_beta_extremes_are_finite(self):
        for beta in (1.0, 1e6):
            with self.subTest(beta=beta):
                b = BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, beta, 0.7)
                r = solve_nodal(b)
                for x in (r.ib_a, r.ic_a, r.ie_a, r.vce_v, r.vb_v, r.ve_v, r.vc_v):
                    self.assertTrue(math.isfinite(x), str(x))


class TestCompare(unittest.TestCase):
    def test_compare_flags_agreement(self):
        b = BiasInput(12.0, 47000.0, 10000.0, 2200.0, 470.0, 150.0, 0.7)
        rows = compare(solve_thevenin(b), solve_nodal(b))
        self.assertEqual([r.name for r in rows], ["IC", "IE", "VCE"])
        for row in rows:
            self.assertTrue(row.matches, row)
            self.assertLess(row.difference, 1e-9)

    def test_compare_flags_mismatch(self):
        base = BiasResult(1e-5, 2.0e-3, 2.01e-3, 5.0, 2.0, 1.3, 6.3, "active", ())
        other = BiasResult(1e-5, 2.5e-3, 2.01e-3, 5.0, 2.0, 1.3, 6.3, "active", ())
        rows = compare(base, other)
        by_name = {r.name: r for r in rows}
        self.assertFalse(by_name["IC"].matches)
        self.assertTrue(by_name["IE"].matches)
        self.assertTrue(by_name["VCE"].matches)
