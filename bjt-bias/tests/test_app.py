import unittest

from app import create_app


DEFAULT_POST = {
    "vcc": "12.0",
    "vcc_unit": "v",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rc": "2.2",
    "rc_unit": "kohm",
    "re": "1.0",
    "re_unit": "kohm",
    "beta": "100",
    "vbe": "0.70",
    "vbe_unit": "v",
}


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_get_shows_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{name}"', body)

    def test_get_shows_unit_selects(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="r1_unit"', body)
        self.assertIn('name="vcc_unit"', body)
        self.assertIn("kΩ", body)
        self.assertIn("mV", body)

    def test_get_shows_lab_header_and_goal(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("Lab 02: BJT DC Bias Web App", body)
        self.assertIn("Week 2 Goal", body)
        self.assertIn("Computer Programming for Electrical Engineers", body)

    def test_post_valid_shows_results(self):
        response = self.client.post("/", data=DEFAULT_POST)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.23", body)  # IC (mA)
        self.assertIn("12.3", body)  # IB (uA)
        self.assertIn("8.05", body)  # VCE (V)
        self.assertNotIn("Saturation", body)
        self.assertIn("Active", body)
        self.assertIn("ตรงกัน", body)

    def test_same_value_different_units_gives_same_result(self):
        kohm = self.client.post("/", data=DEFAULT_POST).get_data(as_text=True)
        ohm_data = dict(DEFAULT_POST)
        ohm_data.update({"r1": "100000", "r1_unit": "ohm", "r2": "22000", "r2_unit": "ohm",
                         "rc": "2200", "rc_unit": "ohm", "re": "1000", "re_unit": "ohm"})
        ohm = self.client.post("/", data=ohm_data).get_data(as_text=True)
        self.assertIn("1.23", ohm)
        self.assertIn("8.05", ohm)
        self.assertEqual(kohm.count("1.23"), ohm.count("1.23"))

    def test_millivolts_gives_same_result(self):
        data = dict(DEFAULT_POST)
        data.update({"vcc": "12000", "vcc_unit": "mv", "vbe": "700", "vbe_unit": "mv"})
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("1.23", body)
        self.assertIn("8.05", body)

    def test_unknown_unit_does_not_crash(self):
        data = dict(DEFAULT_POST)
        data["r1_unit"] = "furlong"
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('class="error"', response.get_data(as_text=True))

    def test_form_echoes_entered_value(self):
        data = dict(DEFAULT_POST)
        data["r1"] = "7"
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn('value="7"', body)

    def test_status_card_switches_when_saturated(self):
        data = dict(DEFAULT_POST)
        data.update({"rc": "100000", "rc_unit": "ohm"})
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("Saturation", body)
        self.assertNotIn("Active region approximation OK", body)

    def test_status_card_switches_when_cutoff(self):
        data = dict(DEFAULT_POST)
        data.update({"r2": "1", "r2_unit": "kohm"})
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("Cutoff", body)
        self.assertNotIn("Active region approximation OK", body)

    def test_post_invalid_zero_resistance(self):
        data = dict(DEFAULT_POST)
        data["r1"] = "0"
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="error"', body)
        self.assertNotIn('class="result-table"', body)

    def test_post_non_numeric(self):
        data = dict(DEFAULT_POST)
        data["rc"] = "abc"
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('class="error"', response.get_data(as_text=True))

    def test_blank_submission_round_trips(self):
        data = dict(DEFAULT_POST)
        data["r1"] = ""
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="error"', body)
        self.assertIn('value="12.0"', body)
        self.assertIn('name="r1"', body)

    def test_form_disables_browser_autofill(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('autocomplete="off"', body)

    def test_get_shows_schematic(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("<svg", body)
        self.assertIn("VCC = 12 V", body)
        self.assertIn("R1", body)

    def test_post_valid_shows_schematic_and_load_line(self):
        body = self.client.post("/", data=DEFAULT_POST).get_data(as_text=True)
        self.assertGreaterEqual(body.count("<svg"), 2)
        self.assertIn("Q (1.23 mA, 8.05 V)", body)
        self.assertIn("VCE (V)", body)
        self.assertIn("VB = 1.94 V", body)


if __name__ == "__main__":
    unittest.main()
