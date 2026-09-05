# Docker (this fork)

## Host OS (Ubuntu 26 and friends)

This fork is **Linux-server OS agnostic** when run with Docker. The app lives in the container; the host only needs Docker Engine + Compose v2.

Supported hosts include **Ubuntu Server 22.04, 24.04, and 26.04**, Debian 11+, and other systemd Linux servers. Details: [`docs/host-compatibility.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/host-compatibility.md).

One-time host prep:

```bash
sudo ./scripts/installers/prepare-host.sh
```

## UI-only laptop / server preview

Default [`docker-compose.yml`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docker-compose.yml) does **not** require `/dev/sr0`.

```bash
mkdir -p data/{home,config,logs,media,music}
cp -n setup/arm.yaml setup/apprise.yaml data/config/
cp -n setup/.abcde.conf data/config/abcde.conf
sudo chown -R "$(id -u):$(id -g)" data
export ARM_UID=$(id -u) ARM_GID=$(id -g) ARM_HOME=$PWD/data
docker compose up -d --build
```

Bind mounts under `./data`:

| Host | Container |
|------|-----------|
| `data/home` | `/home/arm` |
| `data/config` | `/etc/arm/config` (`arm.yaml`, apprise, abcde) |
| `data/logs` | `/home/arm/logs` |
| `data/media` | `/home/arm/media` |
| `data/music` | `/home/arm/music` |

Default login: `admin` / `password`.

## Rebuild after pulling

```bash
git pull
docker compose up -d --build
```

Always `--build` after dependency or Dockerfile changes (e.g. `pyotp` for 2FA).

## Optical drives (real ripping)

Uncomment in compose:

```yaml
devices:
  - /dev/sr0:/dev/sr0
volumes:
  - /run/udev:/run/udev:ro
```

Optional: `ARM_DRIVE_POLL=1` if udev insert events are unreliable.

## Hardware encode devices

See [Hardware-Transcode](Hardware-Transcode). Add `/dev/dri` (Intel/AMD) or NVIDIA GPU flags as documented there.

## Troubleshooting UI startup

```bash
./scripts/diagnose-local.sh
docker compose logs --tail=100
```

Common fixes:

- `sudo chown -R "$(id -u):$(id -g)" data`
- Pull latest `main` (Alembic head / pyotp image fixes)
- Hard-refresh the browser after UI CSS changes

## Image notes

The app is copied into `automaticrippingmachine/arm-dependencies`. This fork’s Dockerfile also `pip install`s `pyotp`, `qrcode`, and `Pillow` for 2FA.
