# Host compatibility (this fork)

## Short answer

**Yes — Ubuntu Server 26.04 is supported** when you run this fork with **Docker Compose**.

The ripping stack runs inside the container image (`automaticrippingmachine/arm-dependencies` + this repo). The host OS mainly needs:

- Linux kernel with Docker Engine + Compose v2
- Optional: optical drive device nodes (`/dev/sr*`) and `/run/udev` for ripping
- Optional: GPU devices for hardware encode

That makes the recommended path **Linux-server OS agnostic**: Ubuntu 22.04 / 24.04 / **26.04**, Debian, and other systemd Linux servers that can run Docker.

## Recommended path (any modern Linux server)

```bash
sudo ./scripts/installers/prepare-host.sh
# then from the clone:
mkdir -p data/{home,config,logs,media,music}
cp -n setup/arm.yaml setup/apprise.yaml data/config/
cp -n setup/.abcde.conf data/config/abcde.conf
sudo chown -R "$(id -u):$(id -g)" data
export ARM_UID=$(id -u) ARM_GID=$(id -g) ARM_HOME=$PWD/data
docker compose up -d --build
```

`prepare-host.sh` installs Docker via [get.docker.com](https://get.docker.com) (multi-distro) and does **not** hard-code an Ubuntu release.

## Support matrix

| Host | Docker Compose (recommended) | Bare-metal installer |
|------|------------------------------|----------------------|
| Ubuntu Server **26.04** | Supported | Not recommended — use Docker |
| Ubuntu Server 24.04 / 22.04 | Supported | Not recommended — use Docker |
| Debian 11/12/13 | Supported | `DebianInstaller.sh` (Debian-focused) |
| Other Linux + Docker | Supported | Unsupported |

## What is *not* host-version-locked

- Python app, Flask UI, Alembic, MakeMKV/HandBrake tooling inside the image
- Compose bind mounts and port `8080`
- Settings / HW encode / multi-user 2FA features in this fork

## Bare-metal note

`scripts/installers/DebianInstaller.sh` targets Debian 11/12 package layouts. On Ubuntu 26 (or non-Debian hosts), use Docker instead of fighting apt package drift.

## Ubuntu 26.04 specifics

Docker Engine officially lists **Ubuntu Resolute 26.04**. If your distro packages of Docker are older, `prepare-host.sh` / get.docker.com installs Engine + Compose plugin from Docker’s repos.
