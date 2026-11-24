import unittest
from unittest.mock import patch

from app import create_app
from spice import default_spice_form
import spice_routes

FORM = default_spice_form()


class TestSpiceRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_spice_shows_form(self):
        body = self.client.get("/spice").get_data(as_text=True)
        for name in ("r1", "rc", "ce", "sin_amp", "ac_fstop", "tran_tstop"):
            self.assertIn(f'name="{name}"', body)
        self.assertIn("startup", body)

    def test_post_invalid_shows_error(self):
        body = self.client.post("/spice", data=dict(FORM, rc="0")).get_data(as_text=True)
        self.assertIn("RC", body)
        self.assertIn("มากกว่าศูนย์", body)
        self.assertNotIn("Success", body)

    @patch.object(spice_routes, "find_ngspice", return_value=None)
    def test_missing_ngspice_shows_setup_hint(self, _):
        body = self.client.post("/spice", data=FORM).get_data(as_text=True)
        self.assertIn("setup_spice.ps1", body)

    def test_get_still_serves_bias_modes(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("Voltage Divider Bias", body)
        self.assertIn("Fixed Bias", body)
        self.assertIn("Emitter Bias", body)
        self.assertIn("/spice", body)


if __name__ == "__main__":
    unittest.main()
