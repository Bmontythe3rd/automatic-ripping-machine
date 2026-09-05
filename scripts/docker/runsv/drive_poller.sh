#!/bin/bash
# Optional ioctl drive poller — enabled with ARM_DRIVE_POLL=1
# Use when Docker udev events are unreliable.

if [ "${ARM_DRIVE_POLL:-0}" != "1" ]; then
  # runit requires a long-running process; sleep forever when disabled
  exec tail -f /dev/null
fi

echo "Starting ARM drive poller (ARM_DRIVE_POLL=1)"
exec /sbin/setuser arm /usr/bin/python3 /opt/arm/scripts/docker/drive_poller.py
