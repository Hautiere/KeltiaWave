#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
PORTAL_HOST="${PORTAL_HOST:-127.0.0.1}"
PORTAL_PORT="${PORTAL_PORT:-4100}"

cd "$PROJECT_DIR/apps/portal"
echo "KeltiaWave Portal: http://$PORTAL_HOST:$PORTAL_PORT"
[ "${OPEN_BROWSER:-1}" = "0" ] || (sleep 1; open "http://$PORTAL_HOST:$PORTAL_PORT" >/dev/null 2>&1 || true) &
exec python3 -m http.server "$PORTAL_PORT" --bind "$PORTAL_HOST"
