#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$PROJECT_DIR/apps/corpus"
[ -d node_modules ] || npm ci --no-audit --no-fund
echo "KeltiaWave Corpus: http://127.0.0.1:4200"
[ "${OPEN_BROWSER:-1}" = "0" ] || (sleep 2; open http://127.0.0.1:4200 >/dev/null 2>&1 || true) &
exec npm start
