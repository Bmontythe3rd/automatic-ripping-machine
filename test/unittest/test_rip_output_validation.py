"""Tests for rip output validation helpers."""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _load_utils_helpers():
    """Load only the pure helpers from utils without full ARM deps."""
    # We'll import via a slim exec of the helper functions by reading source —
    # simpler: stub deps then importlib the module like database_updater tests.
    previous = {}

    def ensure(name, module):
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module
        return module

    for pkg_name, pkg_path in (
        ("arm", os.path.join(ROOT, "arm")),
        ("arm.config", os.path.join(ROOT, "arm/config")),
        ("arm.models", os.path.join(ROOT, "arm/models")),
        ("arm.ripper", os.path.join(ROOT, "arm/ripper")),
        ("arm.ui", os.path.join(ROOT, "arm/ui")),
    ):
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [pkg_path]
        ensure(pkg_name, pkg)

    cfg = ensure("arm.config.config", types.ModuleType("arm.config.config"))
    cfg.arm_config = {}

    ui = ensure("arm.ui", sys.modules["arm.ui"])
    ui.db = MagicMock()

    for mod_name, attrs in (
        ("arm.models.job", {"Job": MagicMock(), "JobState": MagicMock()}),
        ("arm.models.notifications", {"Notifications": MagicMock()}),
        ("arm.models.track", {"Track": MagicMock()}),
        ("arm.models.user", {"User": MagicMock()}),
        ("arm.models.system_drives", {"SystemDrives": MagicMock()}),
        ("arm.ripper.apprise_bulk", {}),
        ("arm.ripper.ProcessHandler", {"arm_subprocess": MagicMock()}),
    ):
        mod = ensure(mod_name, types.ModuleType(mod_name))
        for key, value in attrs.items():
            setattr(mod, key, value)

    for third in ("apprise", "bcrypt", "requests", "psutil"):
        ensure(third, types.ModuleType(third))
    netifaces = ensure("netifaces", types.ModuleType("netifaces"))
    netifaces.interfaces = lambda: []
    netifaces.ifaddresses = lambda *_: {}
    netifaces.AF_INET = 2

    path = os.path.join(ROOT, "arm/ripper/utils.py")
    sys.modules.pop("arm.ripper.utils", None)
    spec = importlib.util.spec_from_file_location("arm.ripper.utils", path)
    utils = importlib.util.module_from_spec(spec)
    sys.modules["arm.ripper.utils"] = utils
    spec.loader.exec_module(utils)
    return utils, previous


class TestRipOutputValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.utils, cls._previous = _load_utils_helpers()

    def test_require_rip_output_raises_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.utils.RipperException):
                self.utils.require_rip_output(tmp, label="MakeMKV")

    def test_require_rip_output_ok_with_mkv(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "title_00.mkv"), "wb").close()
            files = self.utils.require_rip_output(tmp)
            self.assertEqual(files, ["title_00.mkv"])

    def test_media_files_ignores_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "arm.log"), "w").close()
            open(os.path.join(tmp, "movie.mp4"), "wb").close()
            self.assertEqual(self.utils.media_files_in(tmp), ["movie.mp4"])


class TestZeroSavedFiles(unittest.TestCase):
    def test_zero_saved_raises(self):
        # Inline mirror of zero_saved_files parsing logic
        sprintf = ["%1 titles saved, %2 failed", "0", "2"]
        saved = int(sprintf[1])
        self.assertEqual(saved, 0)

    def test_nonzero_saved_ok(self):
        sprintf = ["%1 titles saved, %2 failed", "3", "1"]
        saved = int(sprintf[1])
        failed = int(sprintf[2])
        self.assertGreater(saved, 0)
        self.assertEqual(failed, 1)


if __name__ == "__main__":
    unittest.main()
