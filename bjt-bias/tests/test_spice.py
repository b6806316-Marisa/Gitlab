import unittest

from spice import build_netlists, default_spice_form, parse_spice_form

DEFAULT_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "rl": "10",
    "c1": "10", "ce": "0", "c2": "10", "bf": "200",
    "sin_amp": "10", "sin_freq": "1000",
    "ac_fstart": "10", "ac_fstop": "1e6", "ac_ppd": "50",
    "tran_tstep": "20", "tran_tstop": "200",
}


class TestParseSpiceForm(unittest.TestCase):
    def test_defaults_convert_to_si(self):
        inp, errors = parse_spice_form(DEFAULT_FORM)
        self.assertEqual(errors, [])
        self.assertEqual(inp.r1_ohm, 100_000)
        self.assertAlmostEqual(inp.c1_f, 10e-6)
        self.assertEqual(inp.ce_f, 0.0)
        self.assertAlmostEqual(inp.sin_amp_v, 10e-3)
        self.assertAlmostEqual(inp.tran_tstop_s, 200e-3)

    def test_default_form_is_valid(self):
        inp, errors = parse_spice_form(default_spice_form())
        self.assertEqual(errors, [])
        self.assertIsNotNone(inp)

    def test_rejects_zero_negative_and_non_numeric(self):
        _, errors = parse_spice_form(dict(DEFAULT_FORM, rc="0"))
        self.assertTrue(any("RC" in e for e in errors))
        _, errors = parse_spice_form(dict(DEFAULT_FORM, r1="abc"))
        self.assertTrue(any("R1" in e for e in errors))
        _, errors = parse_spice_form(dict(DEFAULT_FORM, vcc="-12"))
        self.assertTrue(any("VCC" in e for e in errors))
        _, errors = parse_spice_form(dict(DEFAULT_FORM, ce="-1"))
        self.assertTrue(errors)

    def test_rejects_bad_frequency_and_time_windows(self):
        _, e1 = parse_spice_form(dict(DEFAULT_FORM, ac_fstop="10"))
        _, e2 = parse_spice_form(dict(DEFAULT_FORM, tran_tstep="20", tran_tstop="0.1"))
        _, e3 = parse_spice_form(dict(DEFAULT_FORM, ac_ppd="2"))
        self.assertTrue(e1)
        self.assertTrue(e2)
        self.assertTrue(e3)

    def test_rejects_netlist_injection_text(self):
        _, errors = parse_spice_form(dict(DEFAULT_FORM, r1="1; shell"))
        self.assertTrue(errors)


class TestNetlists(unittest.TestCase):
    def test_netlists_use_inputs_and_three_analyses(self):
        inp, _ = parse_spice_form(DEFAULT_FORM)
        nets = build_netlists(inp)
        self.assertEqual(set(nets), {"op", "ac", "tran"})
        self.assertIn("R1 1 2 100000", nets["op"])
        self.assertIn("BF=200", nets["op"])
        self.assertIn("ac dec 50 10 1000000", nets["ac"])
        self.assertIn("tran 2e-05 0.2", nets["tran"])
        self.assertIn(".op", nets["op"])
        self.assertNotIn(".control", nets["op"])

    def test_zero_ce_omits_bypass_capacitor(self):
        inp, _ = parse_spice_form(DEFAULT_FORM)
        self.assertNotIn("C", "\n".join(
            line for line in build_netlists(inp)["op"].splitlines()
            if line.startswith("CE ")
        ))
        bypassed, _ = parse_spice_form(dict(DEFAULT_FORM, ce="100"))
        self.assertIn("CE 4 0 1e-04", build_netlists(bypassed)["op"])


if __name__ == "__main__":
    unittest.main()
