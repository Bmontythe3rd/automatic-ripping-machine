# Hardware Transcode

## Auto — no vendor key in YAML

Set `HB_HW_AUTO: true` in `arm.yaml`, or use **Settings → System Info → Enable auto HW encode**.

You do **not** configure `nvidia` / `intel` / `amd` in YAML. ARM probes HandBrake at rip time and picks a preset:

**NVIDIA NVENC → Intel QSV → AMD VCN/VCE → software** (`HB_PRESET_DVD` / `HB_PRESET_BD`).

| Vendor | Typical preset |
|--------|----------------|
| NVIDIA | `H.265 NVENC 1080p` |
| Intel | `H.265 QSV 1080p` |
| AMD | `H.264 VCE 1080p` |

## Docker + NVIDIA (required for detection)

Host drivers are not enough — pass the GPU into the container:

```bash
docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d
```

Check:

```bash
docker exec arm-rippers nvidia-smi
docker exec arm-rippers HandBrakeCLI --version 2>&1 | grep -i nvenc
```

Expect: `nvenc: version … is available`. System Info should then show NVIDIA as **available**. Logs should include `HB_HW_AUTO selected …`.

## Intel / AMD

Pass `/dev/dri` and add `video` / `render` groups — see [`docs/hardware-transcode.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/hardware-transcode.md).

## GTX 980

Maxwell can work with NVENC once the container sees the GPU. If H.265 NVENC fails during encode, fall back to software presets or `nvenc_h264` after confirming `nvidia-smi` works **inside** the container.

## If HandBrake has no NVENC

If `HandBrakeCLI --help` lists no `nvenc_*` encoders, the image HandBrake was built without NVENC — ARM cannot invent it. See upstream [Hardware Transcode Nvidia NVENC](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Hardware-Transcode-Nvidia-NVENC).
