# Bare-metal ripping checklist

“Bare metal” here means a **dedicated ripper PC**. Prefer **Docker on the host OS** (Ubuntu 22.04–**26.04**, Debian, etc.) rather than the old Debian-only thick install.

1. On the server: `sudo ./scripts/installers/prepare-host.sh` (installs Docker in an OS-agnostic way).  
2. Clone [this fork](https://github.com/Bmontythe3rd/automatic-ripping-machine) and set up `./data` as in [Docker](Docker).  
3. Uncomment optical `devices` and `/run/udev` mounts.  
4. Set `ARM_UID` / `ARM_GID` to your host user; fix `data/` ownership.  
5. Put MakeMKV key in config if required (`MAKEMKV_PERMA_KEY` / MakeMKV settings).  
6. Configure OMDB or TMDB keys in **Settings → Ripper Settings**.  
7. Enable HW encode only after `/dev/dri` or NVIDIA GPUs are passed through — [Hardware-Transcode](Hardware-Transcode).  
8. Create an Operator account if others will use the UI; enable 2FA on Admin — [Users-and-2FA](Users-and-2FA).  
9. Insert a known DVD/BD and watch **Active rips**; confirm files land under `data/media`.  
10. If detection fails, try `ARM_DRIVE_POLL=1` and check `docker compose logs`.

The legacy `DebianInstaller.sh` path is Debian 11/12–oriented and **not** the Ubuntu 26 path — use Docker instead.

Keep [`docs/WAVES.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/WAVES.md) handy for rollback tags.
