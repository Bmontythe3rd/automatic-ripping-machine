"""Unit tests for rip_with_mkv MakeMKV decision logic (pure copy of the rules)."""
import unittest
from unittest.mock import MagicMock


def rip_with_mkv(current_job, protection=0):
    """Mirror of arm.ripper.arm_ripper.rip_with_mkv — keep in sync."""
    if current_job.disctype == "bluray":
        return True

    if current_job.disctype != "dvd":
        return False

    if protection:
        return True
    if current_job.config.SKIP_TRANSCODE:
        return True
    if current_job.config.RIPMETHOD in ("mkv", "backup", "backup_dvd"):
        return True

    return False


class TestRipWithMkv(unittest.TestCase):
    def _job(self, disctype="dvd", ripmethod="mkv", mainfeature=True,
             skip_transcode=False):
        job = MagicMock()
        job.disctype = disctype
        job.config.RIPMETHOD = ripmethod
        job.config.MAINFEATURE = mainfeature
        job.config.SKIP_TRANSCODE = skip_transcode
        return job

    def test_bluray_always_uses_makemkv(self):
        self.assertTrue(rip_with_mkv(self._job(disctype="bluray"), 0))

    def test_dvd_mkv_uses_makemkv_even_with_mainfeature(self):
        # Regression: MAINFEATURE=true used to skip MakeMKV and HandBrake the device
        self.assertTrue(
            rip_with_mkv(self._job(ripmethod="mkv", mainfeature=True), 0)
        )

    def test_dvd_backup_uses_makemkv(self):
        self.assertTrue(rip_with_mkv(self._job(ripmethod="backup"), 0))

    def test_dvd_protection_forces_makemkv(self):
        self.assertTrue(
            rip_with_mkv(self._job(ripmethod="unknown", mainfeature=True), 1)
        )

    def test_music_never_uses_makemkv(self):
        self.assertFalse(rip_with_mkv(self._job(disctype="music"), 0))


if __name__ == "__main__":
    unittest.main()
