#!/bin/bash
# Starts a built Tippy.app without opening a browser window and checks that it really serves the app.
# Usage: packaging/smoke_mac.sh dist/Tippy.app/Contents/MacOS/Tippy
set -euo pipefail
BINARY="$1"
PORT=8791
HOME_DIR="$(mktemp -d)/tippy-smoke"
mkdir -p "$HOME_DIR"

export TIPPY_HOME="$HOME_DIR" TIPPY_PORT="$PORT" TIPPY_NO_BROWSER=1 LLM_MODE=off
"$BINARY" &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; }
trap cleanup EXIT

ok=""
for _ in $(seq 1 40); do
  if page=$(curl -sf "http://127.0.0.1:$PORT/"); then ok=1; break; fi
  sleep 0.75
done
[ -n "$ok" ] || { echo "Tippy did not answer within 30 seconds."; exit 1; }
echo "$page" | grep -qi tippy || { echo "The start page does not look like Tippy."; exit 1; }
curl -sfI "http://127.0.0.1:$PORT/" | grep -qi "content-security-policy" || { echo "The protective headers are missing."; exit 1; }
curl -sf "http://127.0.0.1:$PORT/api/settings" | grep -q '"language"' || { echo "/api/settings gave an unexpected answer."; exit 1; }
for file in js/app.js js/i18n-es.js css/style.css; do
  curl -sf -o /dev/null "http://127.0.0.1:$PORT/$file" || { echo "$file is missing from the app."; exit 1; }
done
curl -sf "http://127.0.0.1:$PORT/api/content/words?count=5&max_len=4" | grep -q '"items"' || { echo "The built-in content is missing."; exit 1; }
[ -d "$HOME_DIR/data" ] || { echo "The data folder was not created in TIPPY_HOME."; exit 1; }
echo "Smoke test passed for $BINARY"
