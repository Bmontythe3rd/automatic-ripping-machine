# Accessing ARM media (SFTP) and NAS mounts

## Where files live

With default Docker Compose, completed rips are on the **host** at:

```text
<repo>/data/media/completed
```

Inside the container that path is `/home/arm/media/completed`. Ownership on the host matches `ARM_UID`/`ARM_GID` (often your login user, or the `arm` user if you created one).

Find the real host paths:

```bash
docker inspect arm-rippers --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

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

In the SFTP session:

```text
ls
cd /home/arm/media/completed          # if media is under arm's home
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

## Map a NAS and generate a custom Compose file

Interactive configurator (NFS, CIFS/SMB, or an already-mounted `/mnt/...` path):

```bash
./scripts/installers/configure-storage.sh
```

It can:

1. Mount the NAS under `/mnt/...` (and optionally add `/etc/fstab`)
2. Write **`docker-compose.nas.yml`** so only **media** and **music** use the NAS  
   (config/logs/home stay on local disk)

Start ARM with the NAS overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d
```

With NVIDIA + NAS:

```bash
docker compose -f docker-compose.yml -f docker-compose.nvidia.yml -f docker-compose.nas.yml up -d
```

`prepare-host.sh` will also offer to run this configurator at the end of host prep.
