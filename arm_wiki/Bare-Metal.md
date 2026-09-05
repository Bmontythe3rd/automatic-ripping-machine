# Bare-metal ripping checklist

Use this when moving from laptop UI preview to a PC with a Blu-ray drive.

1. Install Docker (or follow thick-client install if you prefer bare metal Python).  
2. Clone [this fork](https://github.com/Bmontythe3rd/automatic-ripping-machine) and set up `./data` as in [Docker](Docker).  
3. Uncomment optical `devices` and `/run/udev` mounts.  
4. Set `ARM_UID` / `ARM_GID` to your host user; fix `data/` ownership.  
5. Put MakeMKV key in config if required (`MAKEMKV_PERMA_KEY` / MakeMKV settings).  
6. Configure OMDB or TMDB keys in **Settings → Ripper Settings**.  
7. Enable HW encode only after `/dev/dri` or NVIDIA GPUs are passed through — [Hardware-Transcode](Hardware-Transcode).  
8. Create an Operator account if others will use the UI; enable 2FA on Admin — [Users-and-2FA](Users-and-2FA).  
9. Insert a known DVD/BD and watch **Active rips**; confirm files land under `data/media`.  
10. If detection fails, try `ARM_DRIVE_POLL=1` and check `docker compose logs`.

Keep [`docs/WAVES.md`](https://github.com/Bmontythe3rd/automatic-ripping-machine/blob/main/docs/WAVES.md) handy for rollback tags.
