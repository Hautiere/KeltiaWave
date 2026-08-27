#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSH_TARGET="${SSH_TARGET:-ubuntu@vps-dc75d8a6.vps.ovh.net}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/apps/keltiawave}"
SLOT="${DEPLOY_SLOT:-candidate}"
REMOTE_RELEASE="$REMOTE_ROOT/releases/$SLOT"
REMOTE_ENV="$REMOTE_ROOT/shared/.env.$SLOT"
COMPOSE_FILE="deploy/ovh/docker-compose.candidate.yml"
APPLY=false

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy-ovh.sh [--apply]

Without --apply, only prints and validates the deployment plan.
With --apply, uploads the code, builds an isolated candidate stack and runs
smoke tests. It never changes Caddy and never stops the current production.

Environment:
  SSH_TARGET   SSH destination (default: ubuntu@vps-dc75d8a6.vps.ovh.net)
  REMOTE_ROOT  Remote KeltiaWave directory
  DEPLOY_SLOT  Candidate slot name (default: candidate)
EOF
}

case "${1:-}" in
  "") ;;
  --apply) APPLY=true ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

command -v ssh >/dev/null || { echo "ssh is required" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync is required" >&2; exit 1; }
[[ -f "$PROJECT_DIR/$COMPOSE_FILE" ]] || { echo "Missing $COMPOSE_FILE" >&2; exit 1; }

echo "Deployment target : $SSH_TARGET"
echo "Candidate release : $REMOTE_RELEASE"
echo "Candidate env     : $REMOTE_ENV"
echo "Public site       : untouched"

if ! $APPLY; then
  echo
  echo "DRY RUN only. Prepare $REMOTE_ENV from deploy/ovh/.env.candidate.example,"
  echo "then rerun with --apply. No SSH command was executed."
  exit 0
fi

echo "[1/6] Read-only server preflight"
ssh "$SSH_TARGET" "set -eu; command -v docker >/dev/null; docker compose version >/dev/null; test -f '$REMOTE_ENV'; test -d \"\$(grep '^MODELS_DIR=' '$REMOTE_ENV' | cut -d= -f2-)\"; df -Pk '$REMOTE_ROOT' | awk 'NR==2 { if (\$4 < 5242880) exit 1 }'"

echo "[2/6] Create isolated release directory"
ssh "$SSH_TARGET" "mkdir -p '$REMOTE_RELEASE' '$REMOTE_ROOT/shared'"

echo "[3/6] Upload versioned source (secrets and user data excluded)"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  --exclude 'dist/' \
  --exclude '*.db' \
  --exclude 'backend/data/' \
  --exclude 'backend/models/*' \
  "$PROJECT_DIR/" "$SSH_TARGET:$REMOTE_RELEASE/"

echo "[4/6] Validate Compose configuration"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' config --quiet"

echo "[5/6] Build and start candidate only"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' up -d --build --remove-orphans"

echo "[6/6] Wait for health and run functional smoke tests"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; bash deploy/ovh/smoke-candidate.sh '$REMOTE_ENV'"

cat <<EOF

Candidate deployed and tested successfully.
Production and Caddy are still untouched.

Next mandatory step before promotion:
  1. copy and verify PostgreSQL + MinIO content in the candidate;
  2. rerun smoke-candidate.sh (it requires at least 105 phrases and 4 lessons);
  3. audit the active Caddy and DNS configuration;
  4. perform a separate, reversible Caddy switch.
EOF
