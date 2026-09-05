# Hardware transcoding (Intel / NVIDIA / AMD)

ARM can auto-select HandBrake hardware presets when `HB_HW_AUTO: true` in `arm.yaml`
(Settings → System Info → “Enable auto HW encode”, or Ripper Settings).

## Priority

When auto is on: **NVIDIA → Intel → AMD → software** (`HB_PRESET_DVD` / `HB_PRESET_BD`).

| Vendor | DVD / typical preset | 4K Blu-ray preset |
|--------|----------------------|-------------------|
| NVIDIA | `H.265 NVENC 1080p` | `H.265 NVENC 2160p 4K` |
| Intel  | `H.265 QSV 1080p` | `H.265 QSV 2160p 4K` |
| AMD    | `H.264 VCE 1080p` | same (build-dependent) |

## Docker host requirements

### Intel QuickSync / AMD VCN

```yaml
# under services.arm in docker-compose.yml
devices:
  - /dev/dri:/dev/dri
group_add:
  - video
  - render
```

Host needs a working `/dev/dri/renderD*` node. The container user `arm` is added to `render` at startup.

### NVIDIA NVENC

Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on the host, then:

```yaml
environment:
  - NVIDIA_DRIVER_CAPABILITIES=all
  - NVIDIA_VISIBLE_DEVICES=all
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Or run with `--gpus all`.

## Verify

In Settings → System Info, the Hardware encode panel should show the vendor as **available**.
Check logs for `HB_HW_AUTO selected … preset`.

If HandBrake in the base image was not built with that encoder, ARM cannot invent it — use software presets or a HandBrake build that includes QSV/NVENC/VCE.

## Rollback

Set `HB_HW_AUTO: false` (or remove the key) in Ripper Settings / `arm.yaml`.
