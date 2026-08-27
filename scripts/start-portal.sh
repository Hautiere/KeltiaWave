#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
PORTAL_HOST="127.0.0.1"
PORTAL_PORT="4100"
PORTAL_URL="http://127.0.0.1:4100/"

cd "$PROJECT_DIR/apps/portal"
if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORTAL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Le port $PORTAL_PORT est déjà utilisé."
  echo "Arrêtez l’application qui utilise ce port, puis relancez ./scripts/start-portal.sh"
  exit 1
fi

echo "KeltiaWave Portal: $PORTAL_URL"
(
  sleep 1
  if command -v open >/dev/null 2>&1; then
    open "$PORTAL_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$PORTAL_URL" >/dev/null 2>&1 || true
  fi
) &
exec python3 -m http.server "$PORTAL_PORT" --bind "$PORTAL_HOST"
