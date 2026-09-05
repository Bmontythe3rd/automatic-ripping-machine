"""HandBrake hardware encoder detection and preset selection."""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from typing import Dict, Optional, Tuple

log = logging.getLogger(__name__)

# Built-in HandBrake presets (names from HandBrakeCLI -z / upstream ARM wiki)
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
        "dvd": "H.264 VCE 1080p",
        "bluray": "H.264 VCE 1080p",
        "bluray_4k": "H.264 VCE 1080p",
    },
}

VENDOR_PRIORITY = ("nvidia", "intel", "amd")


def _run_cmd(argv: list, timeout: int = 60) -> str:
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (completed.stdout or "") + "\n" + (completed.stderr or "")
    except FileNotFoundError:
        return ""
    except subprocess.TimeoutExpired:
        log.warning("Command timed out: %s", " ".join(argv))
        return ""
    except OSError as err:
        log.warning("Command failed (%s): %s", argv, err)
        return ""


def _run_handbrake_probe(handbrake_cli: str) -> str:
    """
    Probe HandBrake for HW encoder status.

    Prefer ``--version`` (prints ``nvenc: version X is available``) and
    ``--help`` (lists ``nvenc_h264`` / ``nvenc_h265`` when compiled in).
    """
    chunks = []
    for args in (
        [handbrake_cli, "--version"],
        [handbrake_cli, "--help"],
        [handbrake_cli],
    ):
        out = _run_cmd(args)
        if out.strip():
            chunks.append(out)
    return "\n".join(chunks)


def _nvidia_device_visible() -> bool:
    """True if NVIDIA device nodes or nvidia-smi look usable here."""
    if any(os.path.exists(p) for p in ("/dev/nvidia0", "/dev/nvidiactl", "/dev/nvidia-uvm")):
        return True
    if shutil.which("nvidia-smi"):
        out = _run_cmd(["nvidia-smi", "-L"], timeout=15)
        if out and re.search(r"GPU\s+\d+:", out) and "failed" not in out.lower():
            return True
    return False


def _parse_hw_from_output(output: str) -> Dict[str, bool]:
    status = {"nvidia": False, "intel": False, "amd": False}
    if not output:
        return status

    # Runtime availability (preferred signal from HandBrakeCLI --version)
    if re.search(r"nvenc:\s*version\s+([0-9.]+)\s+is\s+available", output, re.I):
        status["nvidia"] = True
    elif re.search(r"\bnvenc_h26[45]\b", output, re.I):
        if _nvidia_device_visible():
            status["nvidia"] = True
        else:
            log.warning(
                "HandBrake lists NVENC encoders but no NVIDIA device is visible. "
                "Recreate with: docker compose -f docker-compose.yml "
                "-f docker-compose.nvidia.yml up -d"
            )

    if re.search(r"qsv:\s*is\s+.*?available\s+on", output, re.I) or (
        re.search(r"\bqsv_h26[45]\b", output, re.I) and os.path.isdir("/dev/dri")
    ):
        status["intel"] = True

    if re.search(r"vcn:\s*is\s+.*?available\s+on", output, re.I) or re.search(
        r"vce:\s*is\s+.*?available\s+on", output, re.I
    ):
        status["amd"] = True

    return status


def check_hw_transcode_support(handbrake_cli: str = "HandBrakeCLI") -> Dict[str, bool]:
    """
    Detect NVIDIA NVENC, Intel QSV, and AMD VCN/VCE.

    Automatic — do **not** hard-code the vendor in arm.yaml. Enable
    ``HB_HW_AUTO: true`` and expose the GPU to the container. ARM asks
    HandBrake what encoders are available and picks a matching preset.
    """
    output = _run_handbrake_probe(handbrake_cli)
    status = _parse_hw_from_output(output)
    nvidia_dev = _nvidia_device_visible()

    if not status["nvidia"] and nvidia_dev:
        log.warning(
            "NVIDIA device is visible but HandBrake did not report NVENC. "
            "HandBrakeCLI in the image may be built without NVENC support."
        )
    if not any(status.values()) and not nvidia_dev:
        log.info(
            "No HW encoder detected (no GPU device in this environment). "
            "For NVIDIA: docker compose -f docker-compose.yml "
            "-f docker-compose.nvidia.yml up -d"
        )

    log.info(
        "HW encode probe — nvidia=%s intel=%s amd=%s (nvidia_dev=%s)",
        status["nvidia"],
        status["intel"],
        status["amd"],
        nvidia_dev,
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
    """Return (vendor, preset_name) or None if no HW available."""
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
    """Choose HandBrake preset string for this job."""
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
