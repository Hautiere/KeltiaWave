#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSH_TARGET="${SSH_TARGET:-}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/apps/keltiawave}"
SLOT="${DEPLOY_SLOT:-candidate}"
REMOTE_RELEASE="$REMOTE_ROOT/releases/$SLOT"
REMOTE_ENV="$REMOTE_ROOT/shared/.env.$SLOT"
COMPOSE_FILE="deploy/ovh/docker-compose.candidate.yml"
APPLY=false
WITH_LOCAL_DATA=false
CLONE_FROM_SLOT=""
DEPLOY_REF="${DEPLOY_REF:-origin/main}"

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy-ovh.sh [--apply] [--with-local-data] [--clone-from-slot SLOT]

Without --apply, only prints and validates the deployment plan.
With --apply, uploads the code, builds an isolated candidate stack and runs
smoke tests. It never changes Caddy and never stops the current production.

Options:
  --apply             Execute the staging deployment (default: dry run)
  --with-local-data   Migrate backend/keltiawave.db and backend/data after
                      backing up the staging PostgreSQL and MinIO volumes
  --clone-from-slot   Clone PostgreSQL and MinIO from an existing validated
                      slot (for example: staging) into this isolated slot

Environment:
  SSH_TARGET   Required SSH destination (for example: ubuntu@staging.example.com)
  REMOTE_ROOT  Remote KeltiaWave directory
  DEPLOY_SLOT  Candidate slot name (default: candidate)
  DEPLOY_REF   Git revision to deploy (default: origin/main)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=true ;;
    --with-local-data) WITH_LOCAL_DATA=true ;;
    --clone-from-slot)
      shift
      [[ $# -gt 0 ]] || { echo "--clone-from-slot requires a slot" >&2; exit 2; }
      CLONE_FROM_SLOT="$1"
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

if $WITH_LOCAL_DATA && [[ -n "$CLONE_FROM_SLOT" ]]; then
  echo "Choose either --with-local-data or --clone-from-slot" >&2
  exit 2
fi
if [[ -n "$CLONE_FROM_SLOT" && ! "$CLONE_FROM_SLOT" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Invalid clone source slot: $CLONE_FROM_SLOT" >&2
  exit 2
fi

command -v ssh >/dev/null || { echo "ssh is required" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync is required" >&2; exit 1; }
[[ -n "$SSH_TARGET" ]] || { echo "SSH_TARGET is required" >&2; usage >&2; exit 2; }
[[ -f "$PROJECT_DIR/$COMPOSE_FILE" ]] || { echo "Missing $COMPOSE_FILE" >&2; exit 1; }
git -C "$PROJECT_DIR" rev-parse --verify "$DEPLOY_REF^{commit}" >/dev/null || { echo "Unknown DEPLOY_REF: $DEPLOY_REF" >&2; exit 1; }
DEPLOY_SHA="$(git -C "$PROJECT_DIR" rev-parse "$DEPLOY_REF^{commit}")"
if $WITH_LOCAL_DATA; then
  [[ -f "$PROJECT_DIR/backend/keltiawave.db" ]] || { echo "Missing backend/keltiawave.db" >&2; exit 1; }
  [[ -d "$PROJECT_DIR/backend/data" ]] || { echo "Missing backend/data" >&2; exit 1; }
  [[ -f "$PROJECT_DIR/backend/scripts/migrate_full_sqlite.py" ]] || { echo "Missing migration script" >&2; exit 1; }
fi

echo "Deployment target : $SSH_TARGET"
echo "Candidate release : $REMOTE_RELEASE"
echo "Candidate env     : $REMOTE_ENV"
echo "Public site       : untouched"
echo "Local data import : $WITH_LOCAL_DATA"
echo "Clone source      : ${CLONE_FROM_SLOT:-none}"
echo "Git revision      : $DEPLOY_REF ($DEPLOY_SHA)"

if ! $APPLY; then
  echo
  echo "DRY RUN only. Prepare $REMOTE_ENV from deploy/ovh/.env.$SLOT.example,"
  echo "then rerun with --apply."
  echo "No SSH command was executed."
  exit 0
fi

echo "[1/8] Read-only server preflight"
ssh "$SSH_TARGET" "set -eu; command -v docker >/dev/null; docker compose version >/dev/null; test -f '$REMOTE_ENV'; test -d \"\$(grep '^MODELS_DIR=' '$REMOTE_ENV' | cut -d= -f2-)\"; df -Pk '$REMOTE_ROOT' | awk 'NR==2 { if (\$4 < 5242880) exit 1 }'"

echo "[2/8] Create isolated release directory"
ssh "$SSH_TARGET" "mkdir -p '$REMOTE_RELEASE' '$REMOTE_ROOT/shared'"

echo "[3/8] Upload committed source from $DEPLOY_REF"
SOURCE_ARCHIVE="$(mktemp -t keltiawave-source.XXXXXX.tar.gz)"
trap 'rm -f "$SOURCE_ARCHIVE"' EXIT
git -C "$PROJECT_DIR" archive --format=tar.gz --output="$SOURCE_ARCHIVE" "$DEPLOY_REF"
ssh "$SSH_TARGET" "find '$REMOTE_RELEASE' -mindepth 1 -maxdepth 1 ! -name .migration -exec rm -rf -- {} +"
scp "$SOURCE_ARCHIVE" "$SSH_TARGET:$REMOTE_RELEASE/source.tar.gz"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; tar -xzf source.tar.gz; rm -f source.tar.gz; printf '%s\n' '$DEPLOY_SHA' > DEPLOYED_GIT_SHA"

echo "[4/8] Validate Compose configuration"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' config --quiet"

echo "[5/8] Build and start staging only"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' up -d --build --remove-orphans"

echo "[6/8] Wait for backend health"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' up -d --wait backend"

if $WITH_LOCAL_DATA; then
  BACKUP_NAME="before-local-import-$(date -u +%Y%m%dT%H%M%SZ)"
  REMOTE_BACKUP="$REMOTE_ROOT/shared/backups/$SLOT/$BACKUP_NAME"
  REMOTE_MIGRATION="$REMOTE_RELEASE/.migration"

  echo "[7/8] Back up staging and migrate the validated local dataset"
  ssh "$SSH_TARGET" "mkdir -p '$REMOTE_BACKUP' '$REMOTE_MIGRATION/data'"
  ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T postgres sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc' > '$REMOTE_BACKUP/postgres.dump'"
  ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T minio tar -C /data -czf - . > '$REMOTE_BACKUP/minio.tar.gz'"
  rsync -az "$PROJECT_DIR/backend/keltiawave.db" "$SSH_TARGET:$REMOTE_MIGRATION/keltiawave.db"
  rsync -az --delete "$PROJECT_DIR/backend/data/" "$SSH_TARGET:$REMOTE_MIGRATION/data/"
  ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' cp '$REMOTE_MIGRATION/keltiawave.db' backend:/tmp/keltiawave.db; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' cp '$REMOTE_MIGRATION/data' backend:/tmp/migration-data; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T -e PYTHONPATH=/app backend python /app/scripts/migrate_full_sqlite.py /tmp/keltiawave.db /tmp/migration-data"
else
  if [[ -n "$CLONE_FROM_SLOT" ]]; then
    SOURCE_RELEASE="$REMOTE_ROOT/releases/$CLONE_FROM_SLOT"
    SOURCE_ENV="$REMOTE_ROOT/shared/.env.$CLONE_FROM_SLOT"
    BACKUP_NAME="before-$CLONE_FROM_SLOT-clone-$(date -u +%Y%m%dT%H%M%SZ)"
    REMOTE_BACKUP="$REMOTE_ROOT/shared/backups/$SLOT/$BACKUP_NAME"
    SOURCE_COMPOSE="deploy/ovh/docker-compose.candidate.yml"
    DESTINATION_MINIO_VOLUME="keltiawave-${SLOT}_minio_data"

    echo "[7/8] Back up destination and clone validated $CLONE_FROM_SLOT data"
    ssh "$SSH_TARGET" "set -eu; test -f '$SOURCE_ENV'; test -f '$SOURCE_RELEASE/$SOURCE_COMPOSE'; mkdir -p '$REMOTE_BACKUP'; cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T postgres sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc' > '$REMOTE_BACKUP/destination-postgres.dump'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T minio tar -C /data -czf - . > '$REMOTE_BACKUP/destination-minio.tar.gz'; cd '$SOURCE_RELEASE'; docker compose --env-file '$SOURCE_ENV' -f '$SOURCE_COMPOSE' exec -T postgres sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc' > '$REMOTE_BACKUP/source-postgres.dump'; docker compose --env-file '$SOURCE_ENV' -f '$SOURCE_COMPOSE' exec -T minio tar -C /data -czf - . > '$REMOTE_BACKUP/source-minio.tar.gz'; cd '$REMOTE_RELEASE'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' stop backend minio; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' start postgres; cat '$REMOTE_BACKUP/source-postgres.dump' | docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' exec -T postgres sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists --no-owner'; docker run --rm --entrypoint /bin/sh -v '$DESTINATION_MINIO_VOLUME:/data' -v '$REMOTE_BACKUP:/backup:ro' quay.io/minio/minio:latest -c 'find /data -mindepth 1 -delete; tar -C /data -xzf /backup/source-minio.tar.gz'; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' up -d; docker compose --env-file '$REMOTE_ENV' -f '$COMPOSE_FILE' up -d --wait backend"
  else
    echo "[7/8] Skip dataset migration"
  fi
fi

echo "[8/8] Run functional smoke tests"
ssh "$SSH_TARGET" "cd '$REMOTE_RELEASE'; bash deploy/ovh/smoke-candidate.sh '$REMOTE_ENV'"

cat <<EOF

Staging deployed and tested successfully.
Production and Caddy are still untouched.

Next mandatory step before promotion:
  1. perform browser acceptance tests through an SSH tunnel or staging domain;
  2. audit the active Caddy and DNS configuration;
  3. create fresh production backups;
  4. perform a separate, reversible Caddy switch.
EOF
