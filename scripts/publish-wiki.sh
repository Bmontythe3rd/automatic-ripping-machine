#!/usr/bin/env bash
# Publish arm_wiki/ pages to the GitHub Wiki for this fork.
# Prerequisites:
#   1. Wiki feature enabled (Settings → General → Features → Wikis) — already done for this fork
#   2. One-time: open https://github.com/Bmontythe3rd/automatic-ripping-machine/wiki
#      and click "Create the first page" (saves a blank Home). Until then .wiki.git 404s.
#   3. Authenticated git for Bmontythe3rd (same credentials as `git push fork`)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_DIR="$(mktemp -d)"
trap 'rm -rf "$WIKI_DIR"' EXIT

REPO_WIKI="https://github.com/Bmontythe3rd/automatic-ripping-machine.wiki.git"
SRC="$ROOT/arm_wiki"

echo "Cloning wiki → $WIKI_DIR"
if ! git clone "$REPO_WIKI" "$WIKI_DIR"; then
  echo "Clone failed. Enable the Wiki in GitHub repo settings, add a blank Home page once, then re-run."
  exit 1
fi

cp -f "$SRC/Home.md" "$WIKI_DIR/Home.md"
cp -f "$SRC/_Sidebar.md" "$WIKI_DIR/_Sidebar.md"
cp -f "$SRC/Docker.md" "$WIKI_DIR/Docker.md"
cp -f "$SRC/Waves-and-Rollback.md" "$WIKI_DIR/Waves-and-Rollback.md"
cp -f "$SRC/Settings-GUI.md" "$WIKI_DIR/Settings-GUI.md"
cp -f "$SRC/Hardware-Transcode.md" "$WIKI_DIR/Hardware-Transcode.md"
cp -f "$SRC/Users-and-2FA.md" "$WIKI_DIR/Users-and-2FA.md"
cp -f "$SRC/Bare-Metal.md" "$WIKI_DIR/Bare-Metal.md"
cp -f "$SRC/FAQ.md" "$WIKI_DIR/FAQ.md"

cd "$WIKI_DIR"
git add -A
if git diff --cached --quiet; then
  echo "Wiki already up to date."
  exit 0
fi
git commit -m "Sync fork wiki from arm_wiki/"
git push
echo "Published: https://github.com/Bmontythe3rd/automatic-ripping-machine/wiki"
