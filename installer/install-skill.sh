#!/usr/bin/env bash
set -euo pipefail

# One-line usage examples:
#   curl -fsSL https://raw.githubusercontent.com/YoujunZhao/A-Share-Claw/main/installer/install-skill.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/YoujunZhao/A-Share-Claw/main/installer/install-skill.sh | TARGET=openclaw bash
#   curl -fsSL https://raw.githubusercontent.com/YoujunZhao/A-Share-Claw/main/installer/install-skill.sh | TARGET=codex bash

TARGET="${TARGET:-both}" # openclaw|codex|both
REPO_URL="${REPO_URL:-https://github.com/YoujunZhao/A-Share-Claw.git}"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "[a-share-claw] cloning repo..."
git clone --depth=1 "$REPO_URL" "$TMP_DIR/repo" >/dev/null 2>&1

SRC="$TMP_DIR/repo/skills/a-share-claw"
if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "[a-share-claw] SKILL.md not found in repo" >&2
  exit 1
fi

install_to_openclaw() {
  local dst="$HOME/.openclaw/skills/a-share-claw"
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  cp -R "$SRC" "$dst"
  echo "[a-share-claw] installed for OpenClaw -> $dst"
}

install_to_codex() {
  local dst1="$HOME/.agents/skills/a-share-claw"
  local dst2="$HOME/.codex/skills/a-share-claw"

  mkdir -p "$(dirname "$dst1")"
  rm -rf "$dst1"
  cp -R "$SRC" "$dst1"
  echo "[a-share-claw] installed for Codex(.agents) -> $dst1"

  mkdir -p "$(dirname "$dst2")"
  rm -rf "$dst2"
  cp -R "$SRC" "$dst2"
  echo "[a-share-claw] installed for Codex(.codex) -> $dst2"
}

case "$TARGET" in
  openclaw)
    install_to_openclaw
    ;;
  codex)
    install_to_codex
    ;;
  both)
    install_to_openclaw
    install_to_codex
    ;;
  *)
    echo "[a-share-claw] invalid TARGET=$TARGET (use openclaw|codex|both)" >&2
    exit 1
    ;;
esac

echo "[a-share-claw] done. Restart session to load new skill."
