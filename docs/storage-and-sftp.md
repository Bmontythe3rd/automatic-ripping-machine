# Accessing ARM media (SFTP) and NAS mounts

## Why the UI shows `/home/arm/media/...`

The STORAGE widget and `arm.yaml` use **container-internal** paths:

| Setting | Typical value (do not change for Docker) |
|---------|------------------------------------------|
| `TRANSCODE_PATH` | `/home/arm/media/transcode/` |
| `COMPLETED_PATH` | `/home/arm/media/completed/` |

Those paths are correct **inside** the `arm-rippers` container. They are **not**
a claim that files live on the host system disk under `/home/arm`.

Where bits actually land on the server is the Docker **volume bind Source**:

| Default compose (system/repo disk) | NAS overlay |
|------------------------------------|-------------|
| `<repo>/data/media` → `/home/arm/media` | `/mnt/arm-media` → `/home/arm/media` |

**Do not** edit `arm.yaml` to point at `/mnt/...`. Remap the host side of the
volume (this doc + `configure-storage.sh`). Keep container paths as
`/home/arm/media/...`.

The STORAGE card labels:

- **Container:** path from `arm.yaml` (always `/home/arm/media/...` in Docker)
- **Host:** bind source when discoverable (`ARM_HOST_MEDIA` or mountinfo)
- **Free space:** capacity of the filesystem that backs that bind (NAS if mapped)

## Where files live (default)

With default Docker Compose, completed rips are on the **host** at:

```text
<repo>/data/media/completed
```

Inside the container that path is `/home/arm/media/completed`. Ownership on the host matches `ARM_UID`/`ARM_GID` (often your login user, or the `arm` user if you created one).

### Confirm with `docker inspect`

```bash
docker inspect arm-rippers --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

Example when still on repo disk:

```text
/path/to/automatic-ripping-machine/data/media -> /home/arm/media
```

Example when NAS overlay is active:

```text
/mnt/arm-media -> /home/arm/media
/mnt/arm-media/music -> /home/arm/music
```

Also:

```bash
docker exec arm-rippers printenv ARM_HOST_MEDIA ARM_HOST_MUSIC
```

## Point Completed / Transcode at a NAS (host remap)

Interactive configurator (NFS, CIFS/SMB, or an already-mounted `/mnt/...` path):

```bash
./scripts/installers/configure-storage.sh
```

It will:

1. Mount the NAS under `/mnt/...` (optional; can also use an existing mount)
2. Create `completed`, `raw`, and `transcode` under that mount
3. Write **`docker-compose.nas.yml`** so only **media** and **music** use the NAS  
   (config/logs/home stay on local disk)
4. Set `ARM_HOST_MEDIA` / `ARM_HOST_MUSIC` so the UI can show **Host:** paths

Reference overlay (tracked example): [`docker-compose.nas.example.yml`](../docker-compose.nas.example.yml).

Start ARM with the NAS overlay (recreate so mounts apply):

```bash
docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d
```

With NVIDIA + NAS:

```bash
docker compose -f docker-compose.yml -f docker-compose.nvidia.yml -f docker-compose.nas.yml up -d
```

Then re-check:

```bash
docker inspect arm-rippers --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

You want `/home/arm/media` sourced from your `/mnt/...` path, not `<repo>/data/media`.
After refresh, STORAGE should show **Host:** `/mnt/.../transcode` and `/mnt/.../completed`.

`prepare-host.sh` will also offer to run this configurator at the end of host prep.

## SFTP as the `arm` user

On the server:

```bash
# Create arm user if missing (prepare-host can do this with --create-arm-user)
sudo ./scripts/installers/prepare-host.sh --create-arm-user

# Set a password (or use ssh-copy-id instead)
sudo passwd arm
```

From your laptop:

```bash
sftp arm@YOUR_SERVER_IP
# or with a key:
ssh-copy-id arm@YOUR_SERVER_IP
sftp arm@YOUR_SERVER_IP
```

In the SFTP session, `cd` to the **host** path from `docker inspect` (not necessarily `/home/arm/...`):

```text
ls
cd /mnt/arm-media/completed          # NAS layout
# or
cd /path/to/automatic-ripping-machine/data/media/completed
get -r .
```

If files are owned by your normal Linux user instead:

```bash
sftp YOUR_USER@YOUR_SERVER_IP
cd ~/automatic-ripping-machine/data/media/completed
get -r .
```
