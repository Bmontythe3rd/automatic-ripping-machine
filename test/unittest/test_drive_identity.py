import importlib.util
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MODULE_PATH = os.path.join(ROOT, "arm/ui/settings/drive_identity.py")


def _load_drive_identity():
    spec = importlib.util.spec_from_file_location("drive_identity", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drive_identity = _load_drive_identity()
resolve_drive_identity = drive_identity.resolve_drive_identity


class TestDriveIdentity(unittest.TestCase):
    def test_uses_provided_serial_id(self):
        serial_id, name = resolve_drive_identity(
            "/dev/sr0", "LG", "BH16NS40", "ABC123", "LG_BH16NS40_ABC123"
        )
        self.assertEqual(serial_id, "LG_BH16NS40_ABC123")
        self.assertEqual(name, "LG_BH16NS40_ABC123")

    def test_builds_from_maker_model_serial(self):
        serial_id, name = resolve_drive_identity("/dev/sr0", "LG", "BH16NS40", "ABC123", "")
        self.assertEqual(serial_id, "LG|BH16NS40|ABC123")
        self.assertEqual(name, serial_id)

    def test_falls_back_to_mount_when_udev_empty(self):
        serial_id, name = resolve_drive_identity("/dev/sr1", "", "", "", None)
        self.assertEqual(serial_id, "optical-sr1")
        self.assertEqual(name, "optical-sr1")

    def test_never_returns_empty(self):
        serial_id, name = resolve_drive_identity("", None, None, None, "  ")
        self.assertTrue(serial_id)
        self.assertTrue(name)


if __name__ == "__main__":
    unittest.main()
