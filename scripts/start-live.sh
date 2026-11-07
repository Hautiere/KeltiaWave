#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$PROJECT_DIR/apps/live"
[ -d node_modules ] || npm ci --no-audit --no-fund
echo "KeltiaWave Live: http://127.0.0.1:4800"
[ "${OPEN_BROWSER:-1}" = "0" ] || (sleep 2; open http://127.0.0.1:4800 >/dev/null 2>&1 || true) &
exec npm start
