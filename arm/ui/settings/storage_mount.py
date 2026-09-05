"""
Resolve container storage paths to host bind-mount sources.

ARM's arm.yaml paths (e.g. /home/arm/media/completed) are always
container-internal. The real disk location is whatever Docker bind-mounted
on the host — often a NAS under /mnt/... via docker-compose.nas.yml.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


# Default in-container media roots (must stay aligned with setup/arm.yaml).
CONTAINER_MEDIA_ROOT = "/home/arm/media"
CONTAINER_MUSIC_ROOT = "/home/arm/music"


def _normalize(path: str) -> str:
    if not path:
        return ""
    # Prefer realpath when the path exists; otherwise only collapse //.
    try:
        if os.path.exists(path):
            return os.path.realpath(path)
    except OSError:
        pass
    return os.path.normpath(path)


def _under(path: str, root: str) -> Optional[str]:
    """Return relative suffix ('' or '/...') if path is under root, else None."""
    path_n = _normalize(path).rstrip("/") or "/"
    root_n = _normalize(root).rstrip("/") or "/"
    if path_n == root_n:
        return ""
    prefix = root_n + "/"
    if path_n.startswith(prefix):
        return path_n[len(root_n):]  # includes leading /
    return None


def host_path_from_env(container_path: str, environ=None) -> Optional[str]:
    """
    Map container media/music paths using ARM_HOST_MEDIA / ARM_HOST_MUSIC.

    These are set by docker-compose.nas.yml (and optionally base compose).
    """
    env = os.environ if environ is None else environ
    host_media = (env.get("ARM_HOST_MEDIA") or "").strip()
    host_music = (env.get("ARM_HOST_MUSIC") or "").strip()

    if host_media:
        rel = _under(container_path, CONTAINER_MEDIA_ROOT)
        if rel is not None:
            return (host_media.rstrip("/") + rel) if rel else host_media.rstrip("/") or host_media

    if host_music:
        rel = _under(container_path, CONTAINER_MUSIC_ROOT)
        if rel is not None:
            return (host_music.rstrip("/") + rel) if rel else host_music.rstrip("/") or host_music

    return None


def host_path_from_mountinfo(
    container_path: str,
    mountinfo_text: Optional[str] = None,
) -> Optional[str]:
    """
    Best-effort host path from /proc/self/mountinfo bind-mount 'root' fields.

    For a Docker bind of /mnt/nas/media -> /home/arm/media, mountinfo typically
    has root=/mnt/nas/media and mountpoint=/home/arm/media. Subpaths append.
    Returns None when the covering mount has root='/' (overlay / unknown).
    """
    path = _normalize(container_path)
    if not path:
        return None

    if mountinfo_text is None:
        try:
            with open("/proc/self/mountinfo", encoding="utf-8") as handle:
                mountinfo_text = handle.read()
        except OSError:
            return None

    best: Optional[Tuple[int, str]] = None  # (mountpoint_len, host_path)

    for line in mountinfo_text.splitlines():
        parts = line.split()
        if len(parts) < 10:
            continue
        try:
            sep = parts.index("-")
        except ValueError:
            continue
        root = parts[3]
        mountpoint = parts[4]
        # Optional fields may contain spaces encoded; mountpoint is always field 5
        # before optional fields... per man proc_pid_mountinfo, fields 7+ are
        # optional until '-', so mountpoint is always index 4.
        mp_n = mountpoint.rstrip("/") or "/"
        path_n = path.rstrip("/") or "/"
        if path_n != mp_n and not path_n.startswith(mp_n + "/"):
            continue
        if root == "/":
            # Container rootfs / overlay — no distinct host bind path.
            continue
        if path_n == mp_n:
            host = root.rstrip("/") or root
        else:
            rel = path_n[len(mp_n):]
            host = (root.rstrip("/") + rel)
        score = len(mp_n)
        if best is None or score > best[0]:
            best = (score, host)

    return best[1] if best else None


def resolve_host_storage_path(container_path: str, environ=None) -> Optional[str]:
    """Prefer explicit compose env, then mountinfo bind root."""
    from_env = host_path_from_env(container_path, environ=environ)
    if from_env:
        return from_env
    return host_path_from_mountinfo(container_path)
