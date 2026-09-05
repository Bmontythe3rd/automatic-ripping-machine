"""Regression tests for database_updater lock handling via isolated import."""
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
UTILS_PATH = os.path.join(ROOT, "arm/ripper/utils.py")


def _load_utils_with_stubs():
    """Load arm.ripper.utils with fake dependencies — no real config/Flask."""
    previous = {}

    def ensure(name, module):
        previous[name] = sys.modules.get(name)
        sys.modules[name] = module
        return module

    # Package shells with correct __path__ so submodule imports resolve
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

    sys.modules.pop("arm.ripper.utils", None)
    spec = importlib.util.spec_from_file_location("arm.ripper.utils", UTILS_PATH)
    utils = importlib.util.module_from_spec(spec)
    sys.modules["arm.ripper.utils"] = utils
    spec.loader.exec_module(utils)
    return utils, ui.db, previous


class TestDatabaseUpdater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.utils, cls.db, cls._previous = _load_utils_with_stubs()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("arm.ripper.utils", None)
        for name, prev in cls._previous.items():
            if prev is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prev

    def setUp(self):
        self.db.session.reset_mock()

    def test_updater_returns_immediately_on_success(self):
        job = MagicMock(job_id=1)
        self.db.session.commit.side_effect = [None]
        result = self.utils.database_updater({"status": "fail"}, job, wait_time=5)
        self.assertTrue(result)
        self.assertEqual(self.db.session.commit.call_count, 1)

    def test_updater_retries_on_locked_then_succeeds(self):
        job = MagicMock(job_id=2)
        locked = Exception("database is locked")
        self.db.session.commit.side_effect = [locked, locked, None]
        with patch.object(self.utils.time, "sleep"):
            result = self.utils.database_updater({"status": "fail"}, job, wait_time=5)
        self.assertTrue(result)
        self.assertEqual(self.db.session.commit.call_count, 3)

    def test_updater_raises_after_exhausted_retries(self):
        job = MagicMock(job_id=3)
        self.db.session.commit.side_effect = Exception("database is locked")
        with patch.object(self.utils.time, "sleep"):
            with self.assertRaises(RuntimeError):
                self.utils.database_updater({"status": "fail"}, job, wait_time=3)
        self.assertEqual(self.db.session.commit.call_count, 3)

    def test_adder_returns_on_success(self):
        self.db.session.commit.side_effect = [None]
        self.assertTrue(self.utils.database_adder(MagicMock()))
        self.assertEqual(self.db.session.commit.call_count, 1)


if __name__ == "__main__":
    unittest.main()
