# FAQ (fork)

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
