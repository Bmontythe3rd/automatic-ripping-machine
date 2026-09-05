"""Tests for container→host storage path resolution."""
import os
import sys
import unittest
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

SPEC = importlib.util.spec_from_file_location(
    "storage_mount",
    os.path.join(ROOT, "arm/ui/settings/storage_mount.py"),
)
sm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sm)


MOUNTINFO_BIND = """\
21 16 0:20 / / rw,relatime - overlay overlay rw
36 21 8:1 /mnt/arm-media /home/arm/media rw,relatime - ext4 /dev/sda1 rw
42 21 8:1 /mnt/arm-media/music /home/arm/music rw,relatime - ext4 /dev/sda1 rw
"""

MOUNTINFO_DEFAULT = """\
21 16 0:20 / / rw,relatime - overlay overlay rw
36 21 8:1 /home/ubuntu/automatic-ripping-machine/data/media /home/arm/media rw,relatime - ext4 /dev/sda1 rw
"""


class TestStorageMount(unittest.TestCase):
    def test_env_maps_completed_and_transcode(self):
        env = {"ARM_HOST_MEDIA": "/mnt/arm-media", "ARM_HOST_MUSIC": "/mnt/arm-media/music"}
        self.assertEqual(
            sm.host_path_from_env("/home/arm/media/completed/", env),
            "/mnt/arm-media/completed",
        )
        self.assertEqual(
            sm.host_path_from_env("/home/arm/media/transcode/", env),
            "/mnt/arm-media/transcode",
        )
        self.assertEqual(
            sm.host_path_from_env("/home/arm/music", env),
            "/mnt/arm-media/music",
        )

    def test_mountinfo_bind_root(self):
        self.assertEqual(
            sm.host_path_from_mountinfo(
                "/home/arm/media/completed/",
                mountinfo_text=MOUNTINFO_BIND,
            ),
            "/mnt/arm-media/completed",
        )
        self.assertEqual(
            sm.host_path_from_mountinfo(
                "/home/arm/media/transcode",
                mountinfo_text=MOUNTINFO_DEFAULT,
            ),
            "/home/ubuntu/automatic-ripping-machine/data/media/transcode",
        )

    def test_mountinfo_skips_overlay_root(self):
        self.assertIsNone(
            sm.host_path_from_mountinfo("/tmp", mountinfo_text=MOUNTINFO_BIND)
        )

    def test_resolve_prefers_env(self):
        env = {"ARM_HOST_MEDIA": "/mnt/nas"}
        self.assertEqual(
            sm.resolve_host_storage_path("/home/arm/media/completed", environ=env),
            "/mnt/nas/completed",
        )


if __name__ == "__main__":
    unittest.main()
