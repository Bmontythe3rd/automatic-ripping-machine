#!/usr/bin/env bash
# Prepare any modern Linux server host to run this ARM fork via Docker.
# Tested intent: Ubuntu 22.04–26.04 Server, Debian 11+, and other systemd Linux
# distros with Docker Engine. The ARM app runs in a container, so host release
# versions do not need to match the image OS.
set -euo pipefail

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SKIP_DOCKER_INSTALL=0
CREATE_ARM_USER=0

usage() {
  cat <<'EOF'
Usage: prepare-host.sh [OPTIONS]

Prepare a Linux server host for this ARM fork (Docker Compose path).

Options:
  --skip-docker-install   Do not install Docker if missing (only check)
  --create-arm-user       Create a dedicated 'arm' user/group (optional)
  -h, --help              Show this help

Supported hosts (Docker path):
  - Ubuntu Server 22.04, 24.04, 26.04 LTS (and interim releases)
  - Debian 11/12/13
  - Other Linux servers with Docker Engine + Compose v2 plugin

Bare-metal (non-Docker) installs remain Debian-focused; prefer Docker for
OS-agnostic deployments.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-docker-install) SKIP_DOCKER_INSTALL=1 ;;
    --create-arm-user) CREATE_ARM_USER=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; usage; exit 2 ;;
  esac
  shift
done

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo -e "${RED}Run as root (sudo).${NC}"
    exit 1
  fi
}

detect_os() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    HOST_ID="${ID:-unknown}"
    HOST_VERSION_ID="${VERSION_ID:-unknown}"
    HOST_PRETTY="${PRETTY_NAME:-unknown}"
  else
    HOST_ID="unknown"
    HOST_VERSION_ID="unknown"
    HOST_PRETTY="unknown"
  fi
  echo -e "${GREEN}Host:${NC} ${HOST_PRETTY} (${HOST_ID} ${HOST_VERSION_ID})"
}

pkg_install() {
  local packages=("$@")
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y "${packages[@]}"
  elif command -v yum >/dev/null 2>&1; then
    yum install -y "${packages[@]}"
  elif command -v zypper >/dev/null 2>&1; then
    zypper --non-interactive install "${packages[@]}"
  elif command -v pacman >/dev/null 2>&1; then
    pacman -Sy --noconfirm "${packages[@]}"
  else
    echo -e "${YELLOW}No known package manager. Install manually: ${packages[*]}${NC}"
    return 1
  fi
}

install_prereqs() {
  local wanted=()
  command -v curl >/dev/null 2>&1 || wanted+=(curl)
  command -v ca-certificates >/dev/null 2>&1 || true
  # lsscsi is nice-to-have for optical drive inventory
  if ! command -v lsscsi >/dev/null 2>&1; then
    wanted+=(lsscsi)
  fi
  if [[ ${#wanted[@]} -gt 0 ]]; then
    echo -e "${GREEN}Installing host utilities: ${wanted[*]}${NC}"
    pkg_install "${wanted[@]}" || echo -e "${YELLOW}Continuing without optional packages.${NC}"
  fi
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    echo -e "${GREEN}Docker already installed:${NC} $(docker --version)"
  else
    if [[ "${SKIP_DOCKER_INSTALL}" -eq 1 ]]; then
      echo -e "${RED}Docker not found and --skip-docker-install was set.${NC}"
      exit 1
    fi
    echo -e "${GREEN}Installing Docker Engine via get.docker.com (multi-distro)...${NC}"
    curl -fsSL https://get.docker.com | sh
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo -e "${YELLOW}Docker Compose v2 plugin missing; attempting install...${NC}"
    if command -v apt-get >/dev/null 2>&1; then
      pkg_install docker-compose-plugin || true
    fi
  fi

  if docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}Compose:${NC} $(docker compose version)"
  else
    echo -e "${RED}Docker Compose v2 plugin is required (docker compose).${NC}"
    exit 1
  fi

  systemctl enable --now docker >/dev/null 2>&1 || true
}

maybe_create_arm_user() {
  [[ "${CREATE_ARM_USER}" -eq 1 ]] || return 0
  if ! getent group arm >/dev/null 2>&1; then
    groupadd arm
  fi
  if ! id arm >/dev/null 2>&1; then
    useradd -m -g arm -s /bin/bash arm
    echo -e "${YELLOW}Created user 'arm'. Set a password with: passwd arm${NC}"
  fi
  usermod -aG docker arm 2>/dev/null || true
  getent group cdrom >/dev/null 2>&1 && usermod -aG cdrom arm || true
  getent group video >/dev/null 2>&1 && usermod -aG video arm || true
}

add_invoking_user_to_docker() {
  local invoker="${SUDO_USER:-}"
  if [[ -n "${invoker}" && "${invoker}" != "root" ]]; then
    usermod -aG docker "${invoker}" || true
    echo -e "${GREEN}Added ${invoker} to docker group (re-login required).${NC}"
  fi
}

optical_hint() {
  echo -e "${GREEN}Optical devices:${NC}"
  if compgen -G "/dev/sr*" >/dev/null; then
    ls -l /dev/sr* || true
  else
    echo "  (none found — fine for UI-only; uncomment devices in docker-compose.yml for ripping)"
  fi
}

print_next_steps() {
  cat <<EOF

${GREEN}Host is ready for this fork's Docker path.${NC}

Next (as your normal user, from the repo clone):

  mkdir -p data/{home,config,logs,media,music}
  cp -n setup/arm.yaml setup/apprise.yaml data/config/
  cp -n setup/.abcde.conf data/config/abcde.conf
  sudo chown -R "\$(id -u):\$(id -g)" data
  export ARM_UID=\$(id -u) ARM_GID=\$(id -g) ARM_HOME=\$PWD/data
  docker compose up -d --build

Ubuntu Server 26.04 and other modern Linux servers are supported via Docker.
Docs: https://github.com/Bmontythe3rd/automatic-ripping-machine/wiki/Docker
EOF
}

require_root
detect_os
install_prereqs
ensure_docker
maybe_create_arm_user
add_invoking_user_to_docker
optical_hint
print_next_steps
