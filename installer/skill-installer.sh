#!/usr/bin/env bash
set -euo pipefail

# skill-installer style wrapper
# Usage:
#   bash skill-installer.sh install <repo-url> [skill-name]
# Examples:
#   bash skill-installer.sh install https://github.com/YoujunZhao/A-Share-Claw
#   bash skill-installer.sh install https://github.com/YoujunZhao/A-Share-Claw a-share-claw
#   TARGET=openclaw bash skill-installer.sh install <repo-url>

ACTION="${1:-install}"
REPO_URL="${2:-https://github.com/YoujunZhao/A-Share-Claw}"
SKILL_NAME="${3:-}"
TARGET="${TARGET:-both}" # openclaw|codex|both

if [[ "$ACTION" != "install" ]]; then
  echo "[skill-installer] only 'install' is supported" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ "$REPO_URL" == *"raw.githubusercontent.com"* ]]; then
  echo "[skill-installer] please pass GitHub repo URL, not raw file URL" >&2
  exit 1
fi

echo "[skill-installer] cloning: $REPO_URL"
git clone --depth=1 "$REPO_URL" "$TMP_DIR/repo" >/dev/null 2>&1 || {
  echo "[skill-installer] clone failed: $REPO_URL" >&2
  exit 1
}

if [[ -z "$SKILL_NAME" ]]; then
  if [[ -d "$TMP_DIR/repo/skills/a-share-claw" ]]; then
    SKILL_NAME="a-share-claw"
  else
    SKILL_NAME="$(find "$TMP_DIR/repo/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | head -n 1 || true)"
  fi
fi

if [[ -z "$SKILL_NAME" ]]; then
  echo "[skill-installer] no skill folder found under repo/skills" >&2
  exit 1
fi

SRC="$TMP_DIR/repo/skills/$SKILL_NAME"
if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "[skill-installer] invalid skill: $SKILL_NAME (SKILL.md missing)" >&2
  exit 1
fi

install_to_openclaw() {
  local dst="$HOME/.openclaw/skills/$SKILL_NAME"
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  cp -R "$SRC" "$dst"
  echo "[skill-installer] installed OpenClaw skill -> $dst"
}

install_to_codex() {
  local dst1="$HOME/.agents/skills/$SKILL_NAME"
  local dst2="$HOME/.codex/skills/$SKILL_NAME"

  mkdir -p "$(dirname "$dst1")"
  rm -rf "$dst1"
  cp -R "$SRC" "$dst1"
  echo "[skill-installer] installed Codex skill(.agents) -> $dst1"

  mkdir -p "$(dirname "$dst2")"
  rm -rf "$dst2"
  cp -R "$SRC" "$dst2"
  echo "[skill-installer] installed Codex skill(.codex) -> $dst2"
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
    echo "[skill-installer] invalid TARGET=$TARGET (use openclaw|codex|both)" >&2
    exit 1
    ;;
esac

echo "[skill-installer] done. restart agent session to load skill."
