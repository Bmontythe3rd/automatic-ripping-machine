# FAQ (fork)

## Does this run on Ubuntu Server 26.04?

Yes — use the **Docker Compose** path. Host prep: `sudo ./scripts/installers/prepare-host.sh`. See [Docker](Docker) and [`docs/host-compatibility.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/host-compatibility.md). The same path works on other modern Linux servers (OS-agnostic).

## Where is Discord?

This fork’s Help page links to **GitHub** and the **wiki** only. Upstream Discord is not used here.

## Settings won’t save / API keys ignored

Use this fork’s Wave 5+ build. Booleans must be `true`/`false` selects; secret fields leave blank to keep existing values. See [Settings-GUI](Settings-GUI).

## UI won’t start after upgrade

1. `git pull` and `docker compose up -d --build`  
2. Confirm image installs pyotp (Wave 7 Dockerfile)  
3. Alembic should auto-migrate on boot; see logs for migrate errors  
4. [Waves-and-Rollback](Waves-and-Rollback)

## Hardware shows “not detected”

Pass `/dev/dri` or NVIDIA devices into the container. HandBrake must list the encoder. See [Hardware-Transcode](Hardware-Transcode).

## Default password

`admin` / `password` — change under **Password** / **Account** and enable 2FA.

## Why did it rip dozens of titles (and keep re-ripping)?

Blu-rays expose many playlists. With **`MAINFEATURE: false`** (default) and **`RIPMETHOD: mkv`**, MakeMKV rips **every title longer than `MINLENGTH`** — including near-duplicate “main movie” playlists and extras. That matches folders full of `*_t01.mkv`, `*_t09.mkv`, … all ~same size.

If MakeMKV then **fails mid-disc**, ARM aborts **before HandBrake**. The disc often stays in the drive, udev fires again, and ARM starts another job — it looks like an endless loop.

### Rip only the main movie next time

In **Settings → Ripper** (or `data/config/arm.yaml`):

```yaml
MAINFEATURE: true
RIPMETHOD: "mkv"
MINLENGTH: "3600"    # optional: skip shorts under ~1 hour
```

Save, then insert the disc again. ARM will pick the longest/largest track (typically `*MainFeature*`) and rip that one before transcoding.

`RIPMETHOD: "backup"` + `MAINFEATURE: true` is an alternate path (full decrypt, then HandBrake main-feature logic). Prefer `mkv` + `MAINFEATURE` for speed.

### Stop a stuck re-rip loop

```bash
# stop ARM from restarting on the same disc
docker compose stop
# or eject from the UI / drive tray, then:
docker exec arm-rippers eject /dev/sr0 || true
docker compose start
```

In the UI, mark/abandon the failed job. Keep the file named like `…MainFeature….mkv` (or the largest ~movie-length file); extras can be deleted.

## Which file is the “real” movie?

Usually the MakeMKV name containing **`MainFeature`** (e.g. `La La Land-FPL_MainFeature_t01.mkv`). If several files are nearly the same size, they are playlist duplicates — keep one, delete the rest.
