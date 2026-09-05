"""HandBrake hardware encoder detection and preset selection."""
from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict, Optional, Tuple

log = logging.getLogger(__name__)

# Built-in HandBrake presets (names from HandBrakeCLI -z / wiki)
HW_PRESETS = {
    "nvidia": {
        "dvd": "H.265 NVENC 1080p",
        "bluray": "H.265 NVENC 1080p",
        "bluray_4k": "H.265 NVENC 2160p 4K",
    },
    "intel": {
        "dvd": "H.265 QSV 1080p",
        "bluray": "H.265 QSV 1080p",
        "bluray_4k": "H.265 QSV 2160p 4K",
    },
    "amd": {
        # VCE/VCN naming varies by HandBrake build; prefer VCN then VCE
        "dvd": "H.264 VCE 1080p",
        "bluray": "H.264 VCE 1080p",
        "bluray_4k": "H.264 VCE 1080p",
    },
}

VENDOR_PRIORITY = ("nvidia", "intel", "amd")


def _run_handbrake_probe(handbrake_cli: str) -> str:
    """Run HandBrakeCLI and return combined output (even on non-zero exit)."""
    try:
        completed = subprocess.run(
            [handbrake_cli],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return (completed.stdout or "") + "\n" + (completed.stderr or "")
    except FileNotFoundError:
        log.warning("HandBrake CLI not found: %s", handbrake_cli)
        return ""
    except subprocess.TimeoutExpired:
        log.warning("HandBrake CLI probe timed out")
        return ""
    except OSError as err:
        log.warning("HandBrake CLI probe failed: %s", err)
        return ""


def check_hw_transcode_support(handbrake_cli: str = "HandBrakeCLI") -> Dict[str, bool]:
    """
    Detect NVIDIA NVENC, Intel QSV, and AMD VCN/VCE from HandBrake probe output.
    """
    status = {"nvidia": False, "intel": False, "amd": False}
    output = _run_handbrake_probe(handbrake_cli)
    if not output:
        return status

    if re.search(r"nvenc:\s*version\s+([0-9.]+)\s+is\s+available", output, re.I):
        status["nvidia"] = True
    if re.search(r"qsv:\s*is\s+.*?available\s+on", output, re.I):
        status["intel"] = True
    # AMD: VCN (newer) or VCE (older wiki wording)
    if re.search(r"vcn:\s*is\s+.*?available\s+on", output, re.I) or re.search(
        r"vce:\s*is\s+.*?available\s+on", output, re.I
    ):
        status["amd"] = True

    log.info(
        "HW encode probe — nvidia=%s intel=%s amd=%s",
        status["nvidia"],
        status["intel"],
        status["amd"],
    )
    return status


def preferred_vendor(hw_status: Dict[str, bool]) -> Optional[str]:
    for vendor in VENDOR_PRIORITY:
        if hw_status.get(vendor):
            return vendor
    return None


def select_hw_preset(
    disctype: str,
    hw_status: Optional[Dict[str, bool]] = None,
    handbrake_cli: str = "HandBrakeCLI",
    prefer_4k: bool = False,
) -> Optional[Tuple[str, str]]:
    """
    Return (vendor, preset_name) or None if no HW available.
    """
    if hw_status is None:
        hw_status = check_hw_transcode_support(handbrake_cli)
    vendor = preferred_vendor(hw_status)
    if not vendor:
        return None

    presets = HW_PRESETS[vendor]
    disc = (disctype or "").lower()
    if disc == "bluray" and prefer_4k:
        return vendor, presets["bluray_4k"]
    if disc == "bluray":
        return vendor, presets["bluray"]
    return vendor, presets["dvd"]


def resolve_presets(
    disctype: str,
    software_preset: str,
    hw_auto: bool,
    handbrake_cli: str = "HandBrakeCLI",
    hw_status: Optional[Dict[str, bool]] = None,
) -> str:
    """
    Choose HandBrake preset string for this job.
    """
    if not hw_auto:
        return software_preset
    selected = select_hw_preset(disctype, hw_status=hw_status, handbrake_cli=handbrake_cli)
    if not selected:
        log.info("HB_HW_AUTO enabled but no HW encoder found; using %s", software_preset)
        return software_preset
    vendor, preset = selected
    log.info("HB_HW_AUTO selected %s preset for %s: %s", vendor, disctype, preset)
    return preset


def config_truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "on")
