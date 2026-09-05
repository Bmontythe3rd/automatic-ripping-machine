"""Unit tests for arm.ui.settings_save (no Flask app required)."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

# Load module directly to avoid arm.ui Flask import side effects
import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "settings_save",
    os.path.join(ROOT, "arm/ui/settings_save.py"),
)
settings_save = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settings_save)


class TestSettingsSave(unittest.TestCase):
    def test_false_bool_not_empty(self):
        current = {"MANUAL_WAIT": False, "OMDB_API_KEY": "abc", "LOGLEVEL": "INFO"}
        merged = settings_save.merge_arm_config_from_form(
            current, {"MANUAL_WAIT": "false", "csrf_token": "x"}
        )
        self.assertEqual(merged["MANUAL_WAIT"], "false")
        self.assertEqual(merged["OMDB_API_KEY"], "abc")

    def test_secret_placeholder_keeps_key(self):
        current = {"OMDB_API_KEY": "secret123", "TMDB_API_KEY": ""}
        merged = settings_save.merge_arm_config_from_form(
            current,
            {
                "OMDB_API_KEY": "********",
                "TMDB_API_KEY": "",
                "csrf_token": "x",
            },
        )
        self.assertEqual(merged["OMDB_API_KEY"], "secret123")
        self.assertEqual(merged["TMDB_API_KEY"], "")

    def test_secret_update(self):
        current = {"OMDB_API_KEY": "old"}
        merged = settings_save.merge_arm_config_from_form(
            current, {"OMDB_API_KEY": "newkey", "csrf_token": "x"}
        )
        self.assertEqual(merged["OMDB_API_KEY"], "newkey")

    def test_coerce_bool(self):
        self.assertEqual(settings_save.coerce_bool_string(""), "false")
        self.assertEqual(settings_save.coerce_bool_string(False), "false")
        self.assertEqual(settings_save.coerce_bool_string("True"), "true")


if __name__ == "__main__":
    unittest.main()
