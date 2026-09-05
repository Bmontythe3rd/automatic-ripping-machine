"""Tests for hardware transcode preset selection."""
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "hw_transcode",
    os.path.join(ROOT, "arm/ripper/hw_transcode.py"),
)
hw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hw)


class TestHwTranscode(unittest.TestCase):
    def test_preferred_vendor_order(self):
        self.assertEqual(
            hw.preferred_vendor({"nvidia": True, "intel": True, "amd": True}),
            "nvidia",
        )
        self.assertEqual(
            hw.preferred_vendor({"nvidia": False, "intel": True, "amd": True}),
            "intel",
        )
        self.assertIsNone(
            hw.preferred_vendor({"nvidia": False, "intel": False, "amd": False})
        )

    def test_resolve_presets_software(self):
        preset = hw.resolve_presets("dvd", "HQ 720p30 Surround", False)
        self.assertEqual(preset, "HQ 720p30 Surround")

    def test_resolve_presets_auto(self):
        status = {"nvidia": False, "intel": True, "amd": False}
        preset = hw.resolve_presets(
            "bluray", "HQ 1080p30 Surround", True, hw_status=status
        )
        self.assertEqual(preset, "H.265 QSV 1080p")

    def test_probe_parses_nvenc(self):
        sample = "nvenc: version 12.0 is available\n"
        with patch.object(hw, "_run_handbrake_probe", return_value=sample):
            status = hw.check_hw_transcode_support("HandBrakeCLI")
        self.assertTrue(status["nvidia"])
        self.assertFalse(status["intel"])

    def test_config_truthy(self):
        self.assertTrue(hw.config_truthy("true"))
        self.assertTrue(hw.config_truthy(True))
        self.assertFalse(hw.config_truthy("false"))


if __name__ == "__main__":
    unittest.main()
