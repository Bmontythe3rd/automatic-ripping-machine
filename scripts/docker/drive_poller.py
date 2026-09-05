#!/usr/bin/env python3
"""
Poll optical drives via CDROM_DRIVE_STATUS and start ARM when a disc appears.

Use this when Docker udev events are unreliable. Run inside the container or
on the host with access to /dev/sr*.

  ARM_DRIVE_POLL=1 python3 /opt/arm/scripts/docker/drive_poller.py

Environment:
  ARM_POLL_INTERVAL   seconds between polls (default: 2)
  ARM_POLL_DEVICES    comma-separated nodes (default: auto-discover /dev/sr*)
  ARM_WRAPPER         path to docker_arm_wrapper.sh
"""

from __future__ import annotations

import fcntl
import glob
import logging
import os
import subprocess
import sys
import time

# From <linux/cdrom.h>
CDS_NO_INFO = 0
CDS_NO_DISC = 1
CDS_TRAY_OPEN = 2
CDS_DRIVE_NOT_READY = 3
CDS_DISC_OK = 4
CDROM_DRIVE_STATUS = 0x5326

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [drive_poller] %(levelname)s %(message)s",
)
log = logging.getLogger("drive_poller")


def disc_status(devpath: str):
    try:
        fd = os.open(devpath, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as err:
        log.debug("open %s failed: %s", devpath, err)
        return None
    try:
        return fcntl.ioctl(fd, CDROM_DRIVE_STATUS, 0)
    except OSError as err:
        log.debug("ioctl %s failed: %s", devpath, err)
        return None
    finally:
        os.close(fd)


def discover_devices() -> list[str]:
    env = os.environ.get("ARM_POLL_DEVICES", "").strip()
    if env:
        return [d.strip() for d in env.split(",") if d.strip()]
    return sorted(glob.glob("/dev/sr[0-9]*"))


def start_rip(devpath: str, wrapper: str) -> None:
    # Pass basename (sr0) to match udev wrapper expectation
    node = os.path.basename(devpath)
    log.info("Disc ready on %s — starting ARM wrapper", devpath)
    try:
        subprocess.Popen(
            [wrapper, node],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as err:
        log.error("Failed to start wrapper for %s: %s", devpath, err)


def main() -> int:
    interval = float(os.environ.get("ARM_POLL_INTERVAL", "2"))
    wrapper = os.environ.get(
        "ARM_WRAPPER",
        "/opt/arm/scripts/docker/docker_arm_wrapper.sh",
    )
    if not os.path.isfile(wrapper):
        log.error("Wrapper not found: %s", wrapper)
        return 1

    # Track last "idle" vs "busy" so we only fire on insert edges
    was_ready: dict[str, bool] = {}
    log.info("Polling optical drives every %.1fs via ioctl", interval)

    while True:
        for dev in discover_devices():
            status = disc_status(dev)
            ready = status == CDS_DISC_OK
            prev = was_ready.get(dev, False)
            if ready and not prev:
                start_rip(dev, wrapper)
            was_ready[dev] = ready if status is not None else prev
        time.sleep(interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
