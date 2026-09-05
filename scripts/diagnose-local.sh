#!/usr/bin/env bash
# Capture ARM local-run diagnostics for debugging UI startup.
set -u
cd "$(dirname "$0")/.."

echo "===== whoami / docker ====="
whoami
id
docker info 2>&1 | head -20
echo
echo "===== compose ps ====="
docker compose ps -a 2>&1
echo
echo "===== data ownership ====="
ls -ln data data/config data/home 2>&1 | head -40
echo
echo "===== last 150 log lines ====="
docker compose logs --tail=150 2>&1
echo
echo "===== armui process in container ====="
docker compose exec -T arm bash -lc 'ps aux | head -30; ss -lntp 2>/dev/null | head || netstat -lntp 2>/dev/null | head' 2>&1 || true
