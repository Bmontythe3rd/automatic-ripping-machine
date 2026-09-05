# Hardware Transcode

Repo doc: [`docs/hardware-transcode.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/hardware-transcode.md).

## Auto mode

Set `HB_HW_AUTO: true` in `arm.yaml`, or use **Settings → System Info → Enable auto HW encode**.

When enabled, rips pick a HandBrake preset in this order:

**NVIDIA NVENC → Intel QSV → AMD VCN/VCE → software** (`HB_PRESET_DVD` / `HB_PRESET_BD`).

| Vendor | Typical preset |
|--------|----------------|
| NVIDIA | `H.265 NVENC 1080p` |
| Intel | `H.265 QSV 1080p` |
| AMD | `H.264 VCE 1080p` |

Existing installs keep auto **off** until you enable it. New `setup/arm.yaml` defaults auto **on**.

## Docker devices

**Intel / AMD** — add under `services.arm`:

```yaml
devices:
  - /dev/dri:/dev/dri
group_add:
  - video
  - render
```

**NVIDIA** — NVIDIA Container Toolkit on the host, then GPUs / `NVIDIA_DRIVER_CAPABILITIES=all` as in the compose comments.

## Verify

System Info should show the encoder as **available**. Job logs should include `HB_HW_AUTO selected …`.

If HandBrake in the base image lacks that encoder, ARM cannot invent it — use software presets or a HandBrake build with HW support.
