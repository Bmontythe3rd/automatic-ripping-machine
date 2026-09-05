#!/usr/bin/env bash
# Legacy entrypoint — prefer prepare-host.sh for OS-agnostic host prep.
# Kept for compatibility with older docs/scripts that call docker-setup.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Note: docker-setup.sh now delegates to prepare-host.sh (Linux-server OS agnostic)."
echo "Preferred: sudo ./scripts/installers/prepare-host.sh"
exec bash "${SCRIPT_DIR}/prepare-host.sh" "$@"
