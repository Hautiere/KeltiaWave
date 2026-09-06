#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT:-8100}/"
FRONTEND_URL="http://127.0.0.1:4600/"
BACKEND_PID=""
FRONTEND_PID=""

url_is_ready() {
  curl --silent --fail --output /dev/null "$1" 2>/dev/null
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local pid="${3:-}"
  local attempt

  for attempt in $(seq 1 120); do
    if url_is_ready "$url"; then
      echo "$name prêt : $url"
      return 0
    fi
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "$name s'est arrêté avant d'être prêt." >&2
      return 1
    fi
    sleep 1
  done

  echo "$name ne répond pas après 120 secondes : $url" >&2
  return 1
}

open_url() {
  [ "${OPEN_BROWSER:-1}" = "0" ] && return 0
  if command -v open >/dev/null 2>&1; then
    open "$1" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1 || true
  fi
}

cleanup() {
  trap - EXIT INT TERM
  [ -z "$FRONTEND_PID" ] || kill "$FRONTEND_PID" 2>/dev/null || true
  [ -z "$BACKEND_PID" ] || kill "$BACKEND_PID" 2>/dev/null || true
  [ -z "$FRONTEND_PID" ] || wait "$FRONTEND_PID" 2>/dev/null || true
  [ -z "$BACKEND_PID" ] || wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if url_is_ready "$BACKEND_URL"; then
  echo "Backend déjà actif : $BACKEND_URL"
else
  echo "Démarrage du backend…"
  "$PROJECT_DIR/scripts/start-backend.sh" &
  BACKEND_PID=$!
  wait_for_url "Backend" "$BACKEND_URL" "$BACKEND_PID"
fi
open_url "$BACKEND_URL"

cd "$PROJECT_DIR/apps/subtitles"
[ -d node_modules ] || npm ci --no-audit --no-fund
echo "Démarrage de KeltiaWave Subtitles…"
npm start &
FRONTEND_PID=$!
wait_for_url "KeltiaWave Subtitles" "$FRONTEND_URL" "$FRONTEND_PID"
open_url "$FRONTEND_URL"

echo "Backend et Subtitles sont actifs. Ctrl+C arrête les services lancés par ce script."
while kill -0 "$FRONTEND_PID" 2>/dev/null; do
  if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Le backend s'est arrêté de manière inattendue." >&2
    exit 1
  fi
  sleep 1
done

wait "$FRONTEND_PID"
