#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_DIR="$HOME/.openclaw/workspace/mx_autotrade"
ENV_FILE="$HOME/.openclaw/mx.env"

mkdir -p "$TARGET_DIR"
cp -f "$SRC_DIR/mx_autotrade/run_autotrade.py" "$TARGET_DIR/"
cp -f "$SRC_DIR/mx_autotrade/daily_review.py" "$TARGET_DIR/"

if [ ! -f "$TARGET_DIR/config.json" ]; then
  cp -f "$SRC_DIR/mx_autotrade/config.example.json" "$TARGET_DIR/config.json"
fi

chmod +x "$TARGET_DIR/run_autotrade.py" "$TARGET_DIR/daily_review.py"

if [ ! -f "$ENV_FILE" ]; then
  cat <<'TIP'
[WARN] Missing ~/.openclaw/mx.env
Please create it first:
  export MX_APIKEY="your_api_key"
  export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
TIP
fi

( crontab -l 2>/dev/null | grep -v 'mx_autotrade' ; \
  echo '24 9 * * 1-5 . $HOME/.openclaw/mx.env && /usr/bin/python3 $HOME/.openclaw/workspace/mx_autotrade/run_autotrade.py >> $HOME/.openclaw/workspace/mx_autotrade/cron.log 2>&1 # mx_autotrade' ; \
  echo '30 10 * * 1-5 . $HOME/.openclaw/mx.env && /usr/bin/python3 $HOME/.openclaw/workspace/mx_autotrade/run_autotrade.py >> $HOME/.openclaw/workspace/mx_autotrade/cron.log 2>&1 # mx_autotrade' ; \
  echo '30 14 * * 1-5 . $HOME/.openclaw/mx.env && /usr/bin/python3 $HOME/.openclaw/workspace/mx_autotrade/run_autotrade.py >> $HOME/.openclaw/workspace/mx_autotrade/cron.log 2>&1 # mx_autotrade' ; \
  echo '10 15 * * 1-5 . $HOME/.openclaw/mx.env && /usr/bin/python3 $HOME/.openclaw/workspace/mx_autotrade/daily_review.py >> $HOME/.openclaw/workspace/mx_autotrade/cron.log 2>&1 # mx_autotrade' ) | crontab -

echo "Installed to $TARGET_DIR"
echo "Cron updated (mx_autotrade)"
