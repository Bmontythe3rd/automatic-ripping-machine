#!/usr/bin/env bash
# Interactive Compose setup wizard for this ARM fork.
#
# Asks for media location, GPU, optical drives, and optional SMB/NFS mounts
# (credentials stored in /etc/arm-nas-credentials mode 600). Writes:
#   - .env                         (ARM_UID/GID/HOME/TZ)
#   - docker-compose.override.yml  (media remaps, optical, GPU — gitignored)
#   - docker-compose.nas.yml       (when media is remapped; optional -f use)
#
# After it finishes you normally only need:
#   docker compose up -d --build
#
# Storage-only / toolkit-only helpers still exist:
#   ./scripts/installers/configure-storage.sh
#   sudo ./scripts/installers/install-nvidia-toolkit.sh
set -euo pipefail

RED=$'\033[1;31m'
GREEN=$'\033[1;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[1;36m'
NC=$'\033[0m'

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_ENV="${ROOT}/.env"
OUT_OVERRIDE="${ROOT}/docker-compose.override.yml"
OUT_NAS="${ROOT}/docker-compose.nas.yml"
CREDENTIALS_FILE="/etc/arm-nas-credentials"

# Choices collected during the wizard
MEDIA_HOST=""
MUSIC_HOST=""
USE_NAS_OVERLAY=0
GPU_KIND="none"          # none | nvidia | intel | amd
OPTICAL_DEVICES=()       # e.g. /dev/sr0
ENABLE_UDEV=0
ARM_DRIVE_POLL=0
TZ_VALUE="${TZ:-UTC}"
ARM_UID_VALUE=""
ARM_GID_VALUE=""
INSTALL_NVIDIA_TOOLKIT=0

prompt() {
  local msg="$1"
  local default="${2:-}"
  local reply
  if [[ -n "${default}" ]]; then
    read -r -p "${msg} [${default}]: " reply || true
    echo "${reply:-$default}"
  else
    read -r -p "${msg}: " reply || true
    echo "${reply}"
  fi
}

prompt_yn() {
  local msg="$1"
  local default="${2:-n}"
  local reply
  local hint="y/N"
  [[ "${default}" =~ ^[Yy]$ ]] && hint="Y/n"
  read -r -p "${msg} [${hint}]: " reply || true
  reply="${reply:-$default}"
  [[ "${reply}" =~ ^[Yy]$ ]]
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo -e "${RED}Need root for: $*${NC}"
    return 1
  fi
}

ensure_dir() {
  local path="$1"
  if [[ -d "${path}" ]]; then
    return 0
  fi
  mkdir -p "${path}" 2>/dev/null || run_as_root mkdir -p "${path}"
}

detect_uid_gid() {
  if id arm >/dev/null 2>&1; then
    ARM_UID_VALUE="$(id -u arm)"
    ARM_GID_VALUE="$(id -g arm)"
  else
    ARM_UID_VALUE="$(id -u)"
    ARM_GID_VALUE="$(id -g)"
  fi
}

detect_gpu_hint() {
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    echo "nvidia"
    return
  fi
  if [[ -e /dev/dri/renderD128 ]] || [[ -d /dev/dri ]]; then
    # Heuristic: prefer intel if i915/xe present, else amd
    if lsmod 2>/dev/null | grep -Eq '^(i915|xe)\b'; then
      echo "intel"
      return
    fi
    if lsmod 2>/dev/null | grep -Eq '^(amdgpu|radeon)\b'; then
      echo "amd"
      return
    fi
    echo "intel"
    return
  fi
  echo "none"
}

list_optical() {
  local d
  for d in /dev/sr[0-9]*; do
    [[ -e "${d}" ]] && echo "${d}"
  done
}

print_intro() {
  cat <<EOF

${CYAN}╔══════════════════════════════════════════════════════════╗
║     ARM Docker Compose setup wizard (this fork)         ║
╚══════════════════════════════════════════════════════════╝${NC}

This is the recommended way to configure Compose for media storage,
GPU encode, optical drives, and optional SMB/NFS mounts.

Repo: ${ROOT}

It will write gitignored local files (.env, docker-compose.override.yml)
so you can usually start with:

  docker compose up -d --build

EOF
}

seed_data_dirs() {
  echo -e "${GREEN}Preparing local data directories and config templates...${NC}"
  mkdir -p "${ROOT}/data"/{home,config,logs,media,music}
  mkdir -p "${ROOT}/data/media"/{raw,transcode,completed}
  if [[ -d "${ROOT}/setup" ]]; then
    cp -n "${ROOT}/setup/arm.yaml" "${ROOT}/data/config/" 2>/dev/null || true
    cp -n "${ROOT}/setup/apprise.yaml" "${ROOT}/data/config/" 2>/dev/null || true
    cp -n "${ROOT}/setup/.abcde.conf" "${ROOT}/data/config/abcde.conf" 2>/dev/null || true
  fi
  # Best-effort ownership for the invoking user
  if [[ "${EUID}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    chown -R "${SUDO_USER}:${SUDO_USER}" "${ROOT}/data" 2>/dev/null || true
  fi
}

ask_timezone() {
  local host_tz=""
  if [[ -r /etc/timezone ]]; then
    host_tz="$(tr -d '[:space:]' </etc/timezone || true)"
  elif [[ -L /etc/localtime ]]; then
    host_tz="$(readlink /etc/localtime | sed 's|.*/zoneinfo/||')"
  fi
  TZ_VALUE="$(prompt "Timezone (IANA, e.g. America/Chicago)" "${host_tz:-UTC}")"
}

ask_media() {
  echo
  echo -e "${GREEN}=== Media storage ===${NC}"
  echo "Completed rips should live where you have space (local disk or NAS)."
  echo "arm.yaml keeps container paths (/home/arm/media/...). We only remap the host bind."
  echo
  echo "  1) Local under this repo (default: ${ROOT}/data/media)"
  echo "  2) Custom local path already on this host"
  echo "  3) Mount SMB/CIFS share (credentials stored securely)"
  echo "  4) Mount NFS export"
  echo "  5) Use an existing mount (e.g. already under /mnt)"
  local choice
  choice="$(prompt "Choose media location [1-5]" "1")"

  case "${choice}" in
    1)
      MEDIA_HOST="${ROOT}/data/media"
      MUSIC_HOST="${ROOT}/data/music"
      USE_NAS_OVERLAY=0
      ensure_dir "${MEDIA_HOST}/completed"
      ensure_dir "${MEDIA_HOST}/raw"
      ensure_dir "${MEDIA_HOST}/transcode"
      ensure_dir "${MUSIC_HOST}"
      ;;
    2|5)
      MEDIA_HOST="$(prompt "Host path for media" "/mnt/arm-media")"
      ensure_dir "${MEDIA_HOST}"
      ensure_dir "${MEDIA_HOST}/completed"
      ensure_dir "${MEDIA_HOST}/raw"
      ensure_dir "${MEDIA_HOST}/transcode"
      if prompt_yn "Use a separate host path for music?" "n"; then
        MUSIC_HOST="$(prompt "Host path for music" "${MEDIA_HOST%/}/music")"
      else
        MUSIC_HOST="${MEDIA_HOST%/}/music"
      fi
      ensure_dir "${MUSIC_HOST}"
      USE_NAS_OVERLAY=1
      ;;
    3)
      MEDIA_HOST="$(setup_cifs)"
      ensure_dir "${MEDIA_HOST}/completed"
      ensure_dir "${MEDIA_HOST}/raw"
      ensure_dir "${MEDIA_HOST}/transcode"
      if prompt_yn "Use a separate host path for music?" "n"; then
        MUSIC_HOST="$(prompt "Host path for music" "${MEDIA_HOST%/}/music")"
      else
        MUSIC_HOST="${MEDIA_HOST%/}/music"
      fi
      ensure_dir "${MUSIC_HOST}"
      USE_NAS_OVERLAY=1
      ;;
    4)
      MEDIA_HOST="$(setup_nfs)"
      ensure_dir "${MEDIA_HOST}/completed"
      ensure_dir "${MEDIA_HOST}/raw"
      ensure_dir "${MEDIA_HOST}/transcode"
      if prompt_yn "Use a separate host path for music?" "n"; then
        MUSIC_HOST="$(prompt "Host path for music" "${MEDIA_HOST%/}/music")"
      else
        MUSIC_HOST="${MEDIA_HOST%/}/music"
      fi
      ensure_dir "${MUSIC_HOST}"
      USE_NAS_OVERLAY=1
      ;;
    *)
      echo -e "${RED}Unknown choice: ${choice}${NC}"
      exit 2
      ;;
  esac

  echo -e "${GREEN}Media host path:${NC} ${MEDIA_HOST}"
  echo -e "${GREEN}Music host path:${NC} ${MUSIC_HOST}"
}

setup_nfs() {
  local server share mount_point
  server="$(prompt "NFS server hostname or IP")"
  share="$(prompt "NFS export path" "/volume1/media")"
  mount_point="$(prompt "Local mount point" "/mnt/arm-media")"

  if command -v apt-get >/dev/null 2>&1; then
    run_as_root apt-get update -y
    run_as_root apt-get install -y nfs-common
  fi
  ensure_dir "${mount_point}"
  local fstab_line="${server}:${share}  ${mount_point}  nfs  defaults,_netdev,nofail  0  0"
  if ! grep -Fq "${server}:${share}" /etc/fstab 2>/dev/null; then
    run_as_root cp -a /etc/fstab "/etc/fstab.bak.arm.$(date +%s)"
    echo "${fstab_line}" | run_as_root tee -a /etc/fstab >/dev/null
    echo -e "${GREEN}Added fstab entry for NFS.${NC}"
  else
    echo -e "${YELLOW}fstab already has an entry for ${server}:${share}${NC}"
  fi
  run_as_root mount "${mount_point}" 2>/dev/null || run_as_root mount -a
  echo "${mount_point}"
}

setup_cifs() {
  local server share mount_point username password uid gid
  server="$(prompt "SMB/CIFS server hostname or IP")"
  share="$(prompt "Share name (e.g. media, or //server/media)" "media")"
  if [[ "${share}" != //* ]]; then
    share="//${server}/${share}"
  fi
  mount_point="$(prompt "Local mount point" "/mnt/arm-media")"
  username="$(prompt "SMB username" "arm")"

  if command -v apt-get >/dev/null 2>&1; then
    run_as_root apt-get update -y
    run_as_root apt-get install -y cifs-utils
  fi

  echo -e "${YELLOW}SMB password is stored only in ${CREDENTIALS_FILE} (mode 600, root-readable).${NC}"
  read -r -s -p "Password: " password || true
  echo

  local tmpcred
  tmpcred="$(mktemp)"
  umask 077
  cat >"${tmpcred}" <<EOF
username=${username}
password=${password}
EOF
  run_as_root cp "${tmpcred}" "${CREDENTIALS_FILE}"
  run_as_root chmod 600 "${CREDENTIALS_FILE}"
  rm -f "${tmpcred}"
  unset password

  ensure_dir "${mount_point}"

  uid="$(id -u)"
  gid="$(id -g)"
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    uid="$(id -u "${SUDO_USER}")"
    gid="$(id -g "${SUDO_USER}")"
  fi
  if id arm >/dev/null 2>&1; then
    uid="$(id -u arm)"
    gid="$(id -g arm)"
  fi

  local fstab_line="${share}  ${mount_point}  cifs  credentials=${CREDENTIALS_FILE},uid=${uid},gid=${gid},iocharset=utf8,file_mode=0664,dir_mode=0775,_netdev,nofail  0  0"
  if ! grep -Fq "${share}" /etc/fstab 2>/dev/null; then
    run_as_root cp -a /etc/fstab "/etc/fstab.bak.arm.$(date +%s)"
    echo "${fstab_line}" | run_as_root tee -a /etc/fstab >/dev/null
    echo -e "${GREEN}Added fstab entry for CIFS.${NC}"
  else
    echo -e "${YELLOW}fstab already has an entry for ${share}${NC}"
  fi
  run_as_root mount "${mount_point}" 2>/dev/null || run_as_root mount -a
  echo -e "${GREEN}Credentials saved at ${CREDENTIALS_FILE} (chmod 600).${NC}"
  echo "${mount_point}"
}

ask_gpu() {
  echo
  echo -e "${GREEN}=== GPU / hardware encode ===${NC}"
  echo "ARM auto-picks NVENC/QSV/VCN when HB_HW_AUTO is on and the GPU is visible"
  echo "inside the container. You do not put a vendor name in arm.yaml."
  local hint
  hint="$(detect_gpu_hint)"
  echo
  if [[ "${hint}" == "nvidia" ]]; then
    echo -e "Detected: ${CYAN}NVIDIA${NC} ($(nvidia-smi -L 2>/dev/null | head -1 || true))"
  elif [[ "${hint}" == "intel" ]]; then
    echo -e "Detected: ${CYAN}Intel /dev/dri${NC}"
  elif [[ "${hint}" == "amd" ]]; then
    echo -e "Detected: ${CYAN}AMD /dev/dri${NC}"
  else
    echo "Detected: no obvious GPU (software encode is fine)"
  fi
  echo
  echo "  1) None (software encode)"
  echo "  2) NVIDIA (NVENC) — uses docker-compose.nvidia.yml overlay bits"
  echo "  3) Intel QuickSync (/dev/dri)"
  echo "  4) AMD VCN (/dev/dri)"
  local default_choice="1"
  case "${hint}" in
    nvidia) default_choice="2" ;;
    intel) default_choice="3" ;;
    amd) default_choice="4" ;;
  esac
  local choice
  choice="$(prompt "Choose GPU [1-4]" "${default_choice}")"
  case "${choice}" in
    1) GPU_KIND="none" ;;
    2)
      GPU_KIND="nvidia"
      if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}nvidia-smi not found. Install host NVIDIA drivers before HW encode will work.${NC}"
      fi
      if ! docker info 2>/dev/null | grep -qi nvidia; then
        if prompt_yn "Install NVIDIA Container Toolkit now? (needed for gpus: all)" "y"; then
          INSTALL_NVIDIA_TOOLKIT=1
        fi
      else
        echo -e "${GREEN}Docker already reports an NVIDIA runtime.${NC}"
      fi
      ;;
    3) GPU_KIND="intel" ;;
    4) GPU_KIND="amd" ;;
    *)
      echo -e "${RED}Unknown choice: ${choice}${NC}"
      exit 2
      ;;
  esac
}

ask_optical() {
  echo
  echo -e "${GREEN}=== Optical drives ===${NC}"
  local found=()
  local d
  while IFS= read -r d; do
    [[ -n "${d}" ]] && found+=("${d}")
  done < <(list_optical)

  if [[ ${#found[@]} -eq 0 ]]; then
    echo "No /dev/sr* devices found (OK for UI-only preview)."
    if prompt_yn "Still add /dev/sr0 + udev mounts for later ripping?" "n"; then
      OPTICAL_DEVICES+=("/dev/sr0")
      ENABLE_UDEV=1
    fi
  else
    echo "Found:"
    local i
    for i in "${!found[@]}"; do
      echo "  ${found[$i]}"
    done
    if prompt_yn "Pass these drives into the container?" "y"; then
      OPTICAL_DEVICES=("${found[@]}")
      ENABLE_UDEV=1
    fi
  fi

  if [[ ${#OPTICAL_DEVICES[@]} -gt 0 ]]; then
    if prompt_yn "Enable ARM_DRIVE_POLL=1 (helps if disc inserts are missed)?" "n"; then
      ARM_DRIVE_POLL=1
    fi
  fi
}

maybe_install_nvidia_toolkit() {
  [[ "${INSTALL_NVIDIA_TOOLKIT}" -eq 1 ]] || return 0
  local toolkit="${SCRIPT_DIR}/install-nvidia-toolkit.sh"
  if [[ ! -x "${toolkit}" ]]; then
    echo -e "${YELLOW}install-nvidia-toolkit.sh missing; skip toolkit install.${NC}"
    return 0
  fi
  echo -e "${GREEN}Running NVIDIA Container Toolkit installer...${NC}"
  run_as_root bash "${toolkit}" || {
    echo -e "${YELLOW}Toolkit install failed. You can retry later:${NC}"
    echo "  sudo ${toolkit}"
  }
}

write_env() {
  detect_uid_gid
  # Allow override during wizard
  ARM_UID_VALUE="$(prompt "ARM_UID (container file ownership)" "${ARM_UID_VALUE}")"
  ARM_GID_VALUE="$(prompt "ARM_GID" "${ARM_GID_VALUE}")"

  cat >"${OUT_ENV}" <<EOF
# Generated by scripts/installers/setup-arm.sh — do not commit
ARM_UID=${ARM_UID_VALUE}
ARM_GID=${ARM_GID_VALUE}
ARM_HOME=${ROOT}/data
TZ=${TZ_VALUE}
ARM_DRIVE_POLL=${ARM_DRIVE_POLL}
EOF

  if [[ "${USE_NAS_OVERLAY}" -eq 1 ]]; then
    cat >>"${OUT_ENV}" <<EOF
ARM_HOST_MEDIA=${MEDIA_HOST}
ARM_HOST_MUSIC=${MUSIC_HOST}
ARM_NAS_MEDIA=${MEDIA_HOST}
ARM_NAS_MUSIC=${MUSIC_HOST}
EOF
  fi

  echo -e "${GREEN}Wrote ${OUT_ENV}${NC}"
}

write_override() {
  local media_block="" gpu_block="" optical_block="" udev_block="" env_extra=""

  if [[ "${USE_NAS_OVERLAY}" -eq 1 ]]; then
    media_block=$(cat <<EOF
    volumes:
      # Longer destination paths override ./data/media and ./data/music from base compose
      - ${MEDIA_HOST}:/home/arm/media
      - ${MUSIC_HOST}:/home/arm/music
EOF
)
    env_extra="${env_extra}
      - ARM_HOST_MEDIA=${MEDIA_HOST}
      - ARM_HOST_MUSIC=${MUSIC_HOST}"
  fi

  case "${GPU_KIND}" in
    nvidia)
      gpu_block=$(cat <<'EOF'
    gpus: all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
EOF
)
      env_extra="${env_extra}
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=all"
      ;;
    intel|amd)
      gpu_block=$(cat <<'EOF'
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
EOF
)
      ;;
  esac

  if [[ ${#OPTICAL_DEVICES[@]} -gt 0 ]]; then
    optical_block="    devices:"
    local dev
    for dev in "${OPTICAL_DEVICES[@]}"; do
      optical_block+=$'\n'"      - ${dev}:${dev}"
    done
    # If intel/amd already opened devices:, merge optical into that block instead
    if [[ "${GPU_KIND}" == "intel" || "${GPU_KIND}" == "amd" ]]; then
      gpu_block="    devices:"
      gpu_block+=$'\n'"      - /dev/dri:/dev/dri"
      for dev in "${OPTICAL_DEVICES[@]}"; do
        gpu_block+=$'\n'"      - ${dev}:${dev}"
      done
      gpu_block+=$'\n'"    group_add:"
      gpu_block+=$'\n'"      - video"
      gpu_block+=$'\n'"      - render"
      optical_block=""
    fi
  fi

  if [[ "${ENABLE_UDEV}" -eq 1 ]]; then
    if [[ "${USE_NAS_OVERLAY}" -eq 1 ]]; then
      # volumes: already started in media_block — append udev lines via separate merge
      media_block+=$'\n'"      - /run/udev:/run/udev:ro"
      media_block+=$'\n'"      - /dev/disk:/dev/disk:ro"
      udev_block=""
    else
      udev_block=$(cat <<'EOF'
    volumes:
      - /run/udev:/run/udev:ro
      - /dev/disk:/dev/disk:ro
EOF
)
    fi
  fi

  # Compose merge: duplicate keys under services.arm get deep-merged for sequences
  # in Compose v2 for volumes/devices; we emit a single coherent override.
  {
    cat <<EOF
# Generated by scripts/installers/setup-arm.sh — do not commit
# Media: ${MEDIA_HOST}
# Music: ${MUSIC_HOST}
# GPU:   ${GPU_KIND}
# Optical: ${OPTICAL_DEVICES[*]:-none}
#
# Start:
#   docker compose up -d --build

services:
  arm:
    environment:
      - ARM_DRIVE_POLL=${ARM_DRIVE_POLL}${env_extra}
EOF
    if [[ -n "${media_block}" ]]; then
      echo "${media_block}"
    elif [[ -n "${udev_block}" ]]; then
      echo "${udev_block}"
    fi
    if [[ -n "${gpu_block}" ]]; then
      echo "${gpu_block}"
    fi
    if [[ -n "${optical_block}" ]]; then
      echo "${optical_block}"
    fi
  } >"${OUT_OVERRIDE}"

  echo -e "${GREEN}Wrote ${OUT_OVERRIDE}${NC}"
}

write_nas_compose() {
  [[ "${USE_NAS_OVERLAY}" -eq 1 ]] || {
    rm -f "${OUT_NAS}" 2>/dev/null || true
    return 0
  }

  cat >"${OUT_NAS}" <<EOF
# Generated by scripts/installers/setup-arm.sh
# Same media remaps as docker-compose.override.yml (for explicit -f use).
#
# Prefer: docker compose up -d   (override.yml is auto-merged)
# Or:     docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d

services:
  arm:
    environment:
      - ARM_HOST_MEDIA=${MEDIA_HOST}
      - ARM_HOST_MUSIC=${MUSIC_HOST}
    volumes:
      - ${MEDIA_HOST}:/home/arm/media
      - ${MUSIC_HOST}:/home/arm/music
EOF
  echo -e "${GREEN}Wrote ${OUT_NAS}${NC}"
}

print_summary() {
  cat <<EOF

${GREEN}=== Setup complete ===${NC}

  Media (host):  ${MEDIA_HOST}  →  /home/arm/media
  Music (host):  ${MUSIC_HOST}  →  /home/arm/music
  GPU:           ${GPU_KIND}
  Optical:       ${OPTICAL_DEVICES[*]:-none}
  UID:GID:       ${ARM_UID_VALUE}:${ARM_GID_VALUE}
  Timezone:      ${TZ_VALUE}

Files:
  ${OUT_ENV}
  ${OUT_OVERRIDE}
$([ "${USE_NAS_OVERLAY}" -eq 1 ] && echo "  ${OUT_NAS}")

${CYAN}Start ARM:${NC}

  cd ${ROOT}
  docker compose up -d --build

Open http://localhost:8080  (default login: admin / password)

Verify mounts:
  docker inspect arm-rippers --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'

EOF

  if [[ "${GPU_KIND}" == "nvidia" ]]; then
    cat <<EOF
NVIDIA checks (after start):
  docker exec arm-rippers nvidia-smi
  docker exec arm-rippers HandBrakeCLI --version 2>&1 | grep -i nvenc

EOF
  fi

  if [[ "${USE_NAS_OVERLAY}" -eq 1 ]]; then
    cat <<EOF
SFTP tip — pull completed rips from another PC:
  sftp YOUR_USER@YOUR_SERVER_IP
  cd ${MEDIA_HOST}/completed
  get -r .

EOF
  fi

  echo "Re-run this wizard anytime:  ./scripts/installers/setup-arm.sh"
  echo "Storage only:                ./scripts/installers/configure-storage.sh"
  echo "Docs: docs/storage-and-sftp.md  docs/hardware-transcode.md"
}

# Drop root for gitignored file writes so the clone owner can edit them.
write_as_repo_user() {
  local target="$1"
  if [[ "${EUID}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    chown "${SUDO_USER}:${SUDO_USER}" "${target}" 2>/dev/null || true
  fi
}

apply_defaults_noninteractive() {
  echo -e "${YELLOW}--defaults: local media, auto GPU detect, optical if present, no prompts.${NC}"
  detect_uid_gid
  if [[ -r /etc/timezone ]]; then
    TZ_VALUE="$(tr -d '[:space:]' </etc/timezone || echo UTC)"
  else
    TZ_VALUE="${TZ:-UTC}"
  fi
  MEDIA_HOST="${ROOT}/data/media"
  MUSIC_HOST="${ROOT}/data/music"
  USE_NAS_OVERLAY=0
  ensure_dir "${MEDIA_HOST}/completed"
  ensure_dir "${MEDIA_HOST}/raw"
  ensure_dir "${MEDIA_HOST}/transcode"
  ensure_dir "${MUSIC_HOST}"
  GPU_KIND="$(detect_gpu_hint)"
  local d
  while IFS= read -r d; do
    [[ -n "${d}" ]] && OPTICAL_DEVICES+=("${d}")
  done < <(list_optical)
  if [[ ${#OPTICAL_DEVICES[@]} -gt 0 ]]; then
    ENABLE_UDEV=1
  fi
  INSTALL_NVIDIA_TOOLKIT=0
}

usage() {
  cat <<'EOF'
Usage: setup-arm.sh [OPTIONS]

Interactive wizard that configures Docker Compose for this ARM fork:
  - where media/music live (local path, SMB/CIFS, NFS, or existing mount)
  - GPU passthrough (none / NVIDIA / Intel / AMD)
  - optical drives + udev
  - writes .env and docker-compose.override.yml (gitignored)

Options:
  --defaults   Non-interactive: local ./data media, auto-detect GPU/optical
  -h, --help   Show this help

SMB passwords go to /etc/arm-nas-credentials with mode 600 (not in git).

After running, start with:
  docker compose up -d --build
EOF
}

main() {
  local use_defaults=0
  case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    --defaults) use_defaults=1 ;;
    "") ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 2 ;;
  esac

  print_intro
  seed_data_dirs

  if [[ "${use_defaults}" -eq 1 ]]; then
    apply_defaults_noninteractive
  else
    ask_timezone
    ask_media
    ask_gpu
    ask_optical
    maybe_install_nvidia_toolkit
  fi

  # write_env prompts for UID/GID confirmation unless --defaults
  if [[ "${use_defaults}" -eq 1 ]]; then
    cat >"${OUT_ENV}" <<EOF
# Generated by scripts/installers/setup-arm.sh — do not commit
ARM_UID=${ARM_UID_VALUE}
ARM_GID=${ARM_GID_VALUE}
ARM_HOME=${ROOT}/data
TZ=${TZ_VALUE}
ARM_DRIVE_POLL=${ARM_DRIVE_POLL}
EOF
    write_as_repo_user "${OUT_ENV}"
    echo -e "${GREEN}Wrote ${OUT_ENV}${NC}"
  else
    write_env
    write_as_repo_user "${OUT_ENV}"
  fi

  write_override
  write_as_repo_user "${OUT_OVERRIDE}"
  write_nas_compose
  if [[ -f "${OUT_NAS}" ]]; then
    write_as_repo_user "${OUT_NAS}"
  fi
  print_summary
}

main "$@"
