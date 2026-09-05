# Automatic Ripping Machine (fork)

This wiki documents **[Bmontythe3rd/automatic-ripping-machine](https://github.com/Bmontythe3rd/automatic-ripping-machine)** — a stabilize-and-modernize fork of the upstream Automatic Ripping Machine.

## Host compatibility

**Docker is the supported, OS-agnostic path** — including **Ubuntu Server 26.04** and other modern Linux servers. See [Docker](Docker) and [`docs/host-compatibility.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/host-compatibility.md).

## What this fork improves

- Reliable SQLite / job DB updates and empty-rip failure detection
- Laptop-friendly Docker Compose for UI preview
- Media-workshop UI (dark graphite + amber)
- Settings GUI that correctly saves OMDB/TMDB and boolean options
- Optional hardware encode auto-select (NVIDIA → Intel → AMD)
- Multi-user accounts (Admin / Operator) with TOTP 2FA

## Quick start (Docker UI)

```bash
git clone https://github.com/Bmontythe3rd/automatic-ripping-machine.git
cd automatic-ripping-machine
sudo ./scripts/installers/prepare-host.sh   # once per host (Ubuntu 26, Debian, …)
mkdir -p data/{home,config,logs,media,music}
cp -n setup/arm.yaml setup/apprise.yaml data/config/
cp -n setup/.abcde.conf data/config/abcde.conf
sudo chown -R "$(id -u):$(id -g)" data
export ARM_UID=$(id -u) ARM_GID=$(id -g) ARM_HOME=$PWD/data
docker compose up -d --build
```

Open **http://localhost:8080** — default login `admin` / `password`.

## Next steps

| Topic | Page |
|-------|------|
| Compose, volumes, optical drives | [Docker](Docker) |
| Waves, tags, rollback | [Waves-and-Rollback](Waves-and-Rollback) |
| OMDB/TMDB and ripper settings | [Settings-GUI](Settings-GUI) |
| NVENC / QSV / VCN | [Hardware-Transcode](Hardware-Transcode) |
| Users and 2FA | [Users-and-2FA](Users-and-2FA) |
| Bare-metal ripping checklist | [Bare-Metal](Bare-Metal) |

## Upstream

This project is based on [automatic-ripping-machine/automatic-ripping-machine](https://github.com/automatic-ripping-machine/automatic-ripping-machine). Prefer **this wiki and this repository** for fork-specific behavior.
