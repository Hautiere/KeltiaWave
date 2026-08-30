#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSH_TARGET="${SSH_TARGET:-}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/apps/keltiawave}"
PRODUCTION_SLOT="production"
STAGING_SLOT="staging"
APPLY=false

if [[ "${1:-}" == "--apply" ]]; then
  APPLY=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--apply]" >&2
  exit 2
fi
[[ -n "$SSH_TARGET" ]] || { echo "SSH_TARGET is required" >&2; exit 2; }

production_release="$REMOTE_ROOT/releases/$PRODUCTION_SLOT"
staging_release="$REMOTE_ROOT/releases/$STAGING_SLOT"
staging_env="$REMOTE_ROOT/shared/.env.$STAGING_SLOT"

echo "Source data       : $PRODUCTION_SLOT"
echo "Destination data  : $STAGING_SLOT"
echo "Application code  : unchanged"
echo "Apply refresh     : $APPLY"

echo "[1/4] Verify production and staging stacks"
ssh "$SSH_TARGET" "set -eu; test -f '$production_release/DEPLOYED_GIT_SHA'; test -f '$staging_release/DEPLOYED_GIT_SHA'; test -f '$REMOTE_ROOT/shared/.env.$PRODUCTION_SLOT'; test -f '$staging_env'; test -f '$staging_release/deploy/ovh/clone-slot-data.sh'"

if ! $APPLY; then
  echo
  echo "DRY RUN passed. No data was copied."
  echo "Rerun with --apply to back up staging and refresh it from production."
  exit 0
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$REMOTE_ROOT/shared/backups/$STAGING_SLOT/before-production-refresh-$timestamp"

echo "[2/4] Back up staging and copy production PostgreSQL and MinIO"
ssh "$SSH_TARGET" "bash '$staging_release/deploy/ovh/clone-slot-data.sh' '$PRODUCTION_SLOT' '$STAGING_SLOT' '$REMOTE_ROOT' '$backup_dir'"

echo "[3/4] Run staging functional smoke tests"
ssh "$SSH_TARGET" "cd '$staging_release'; bash deploy/ovh/smoke-candidate.sh '$staging_env'"

echo "[4/4] Verify production services remain healthy"
ssh "$SSH_TARGET" "set -eu; cd '$production_release'; bash deploy/ovh/smoke-candidate.sh '$REMOTE_ROOT/shared/.env.$PRODUCTION_SLOT' >/dev/null; echo 'Production smoke tests passed.'"

echo
echo "Staging data refreshed successfully from production."
echo "Rollback backup: $backup_dir"
