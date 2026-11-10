import unittest

from app import create_app


DEFAULT_POST = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "2200",
    "re": "470",
    "beta": "150",
    "vbe": "0.7",
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

    def test_post_valid_shows_results(self):
        response = self.client.post("/", data=DEFAULT_POST)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("2.661", body)
        self.assertNotIn("Saturation", body)
        self.assertIn("Active", body)
        self.assertIn("ตรงกัน", body)

    def test_post_invalid_zero_resistance(self):
        data = dict(DEFAULT_POST)
        data["r1"] = "0"
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="error"', body)
        self.assertNotIn("class=\"result-table\"", body)

    def test_post_non_numeric(self):
        data = dict(DEFAULT_POST)
        data["rc"] = "abc"
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="error"', body)

    def test_form_disables_browser_autofill(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        self.assertIn('autocomplete="off"', body)

    def test_get_shows_schematic(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<svg", body)
        self.assertIn("VCC = 12 V", body)
        self.assertIn("R1", body)

    def test_post_valid_shows_schematic_and_load_line(self):
        response = self.client.post("/", data=DEFAULT_POST)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertGreaterEqual(body.count("<svg"), 2)
        self.assertIn("Q (2.66 mA, 4.89 V)", body)
        self.assertIn("VCE (V)", body)
        self.assertIn("VB = 1.96 V", body)

    def test_blank_submission_round_trips(self):
        data = dict(DEFAULT_POST)
        data["r1"] = ""
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="error"', body)
        # entered values should be echoed back in inputs
        self.assertIn('value="12"', body)
        self.assertIn('name="r1"', body)


if __name__ == "__main__":
    unittest.main()
