#!/usr/bin/env bash
# Install NVIDIA Container Toolkit so Docker Compose can use gpus: all /
# docker-compose.nvidia.yml. Host NVIDIA drivers (nvidia-smi) must already work.
set -euo pipefail

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ "${EUID}" -ne 0 ]]; then
  echo -e "${RED}Run as root: sudo $0${NC}"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo -e "${RED}nvidia-smi not found. Install NVIDIA host drivers first, then re-run.${NC}"
  exit 1
fi

echo -e "${GREEN}Host GPU:${NC}"
nvidia-smi -L || true

if command -v snap >/dev/null 2>&1 && snap list docker >/dev/null 2>&1; then
  echo -e "${YELLOW}Docker is installed via snap. GPU passthrough often fails with snap Docker.${NC}"
  echo "Prefer Docker Engine from get.docker.com / docker-ce packages."
fi

echo -e "${GREEN}Installing NVIDIA Container Toolkit...${NC}"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

apt-get update -y
apt-get install -y nvidia-container-toolkit

nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

echo -e "${GREEN}Verifying GPU in a test container...${NC}"
if docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi; then
  echo -e "${GREEN}Toolkit OK.${NC}"
else
  echo -e "${YELLOW}Test container failed. Check: cat /etc/docker/daemon.json && systemctl status docker${NC}"
  echo "If using snap Docker, migrate to docker-ce, then re-run this script."
  exit 1
fi

cat <<EOF

${GREEN}Next — start ARM with the GPU overlay:${NC}

  cd /home/bmontgomery/automatic-ripping-machine   # or your clone path
  docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d --build
  docker exec arm-rippers nvidia-smi
  docker exec arm-rippers HandBrakeCLI --version 2>&1 | grep -i nvenc

EOF
