# Hardware transcoding (Intel / NVIDIA / AMD)

ARM auto-selects HandBrake hardware presets when `HB_HW_AUTO: true` in `arm.yaml`
(Settings → System Info → “Enable auto HW encode”, or Ripper Settings).

## Does it need a YAML GPU setting?

**No.** You do **not** put `nvidia` / `intel` / `amd` in YAML.

1. `HB_HW_AUTO: true` — already the default for new installs  
2. Expose the GPU to the container (Docker) or install drivers (bare metal)  
3. At rip time ARM runs `HandBrakeCLI --version` / `--help`, sees `nvenc: version … is available` (or QSV/VCN), and picks the matching preset  

If HandBrake cannot see the GPU, ARM falls back to `HB_PRESET_DVD` / `HB_PRESET_BD` (software).

## Priority

When auto is on: **NVIDIA → Intel → AMD → software**.

| Vendor | DVD / Blu-ray preset | 4K preset |
|--------|----------------------|-----------|
| NVIDIA | `H.265 NVENC 1080p` | `H.265 NVENC 2160p 4K` |
| Intel  | `H.265 QSV 1080p` | `H.265 QSV 2160p 4K` |
| AMD    | `H.264 VCE 1080p` | same (build-dependent) |

## Docker + NVIDIA (most common miss)

Host drivers alone are not enough. The **container** must receive the GPU:

```bash
# After nvidia-smi works on the host and Container Toolkit is installed:
docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d
```

Verify inside the container:

```bash
docker exec arm-rippers nvidia-smi
docker exec arm-rippers HandBrakeCLI --version 2>&1 | grep -i nvenc
# expect: nvenc: version X.Y is available
```

Also confirm UI **System Info** shows NVIDIA as available.

### Intel QuickSync / AMD VCN

```yaml
# under services.arm in docker-compose.yml
devices:
  - /dev/dri:/dev/dri
group_add:
  - video
  - render
```

## GTX 980 (Maxwell) note

Upstream HandBrake docs often recommend Pascal (1050+) or newer for NVENC. A GTX 980 can still expose NVENC; if H.265 NVENC fails at encode time, set software presets or a HandBrake build/preset that uses `nvenc_h264`. First confirm the container sees the GPU (steps above).

## If HandBrake has no NVENC in the image

ARM cannot invent encoders. If `HandBrakeCLI --help` has no `nvenc_h264` / `nvenc_h265`, the image HandBrake was built without NVENC — rebuild HandBrake with NVENC or use a base image that includes it (see upstream [Hardware Transcode Nvidia NVENC](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Hardware-Transcode-Nvidia-NVENC)).

## Rollback

Set `HB_HW_AUTO: false` in Ripper Settings / `arm.yaml`.
