"""Pure helpers for optical-drive identity (no Flask/DB imports)."""

import os


def resolve_drive_identity(mount, maker="", model="", serial="", serial_id=""):
    """
    Build a non-empty serial_id and display name for an optical drive.

    Docker/udev often omit ID_SERIAL. Empty serial_id collapses multiple drives
    into one DB row and empty names violate the NOT NULL constraint on
    system_drives.name.
    """
    maker = (maker or "").strip()
    model = (model or "").strip()
    serial = (serial or "").strip()
    serial_id = (serial_id or "").strip()
    mount = (mount or "").strip()

    if not serial_id:
        parts = [part for part in (maker, model, serial) if part]
        if parts:
            serial_id = "|".join(parts)
        else:
            mount_name = os.path.basename(mount) or "unknown"
            serial_id = f"optical-{mount_name}"

    display_name = serial_id
    return serial_id, display_name
