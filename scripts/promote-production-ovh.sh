#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSH_TARGET="${SSH_TARGET:-}"
PUBLIC_IPV4="${PUBLIC_IPV4:-}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/apps/keltiawave}"
PRODUCTION_RELEASE="$REMOTE_ROOT/releases/production"
PRODUCTION_ENV="$REMOTE_ROOT/shared/.env.production"
ACTIVE_CADDY="/home/ubuntu/apps/corpus-collaboratif/deploy/ovh/Caddyfile"
DEPLOY_REF="${DEPLOY_REF:-origin/main}"
APPLY=false

[[ "${1:-}" == "--apply" ]] && APPLY=true
[[ -n "$SSH_TARGET" ]] || { echo "SSH_TARGET is required" >&2; exit 2; }
[[ -n "$PUBLIC_IPV4" ]] || { echo "PUBLIC_IPV4 is required" >&2; exit 2; }

EXPECTED_SHA="$(git -C "$PROJECT_DIR" rev-parse "$DEPLOY_REF^{commit}")"
DOMAINS=(
  keltiawave.com
  keltiawave.bzh
  learning.keltiawave.com
  komz.keltiawave.com
  voices.keltiawave.com
  transcribe.keltiawave.com
  record.keltiawave.com
  subtitles.keltiawave.com
  transcription.keltiawave.com
)

echo "Production candidate : $EXPECTED_SHA"
echo "Public IPv4         : $PUBLIC_IPV4"
echo "Caddy switch        : $APPLY"

echo "[1/5] Verify candidate revision, health and content"
ssh "$SSH_TARGET" "set -eu; test \"\$(cat '$PRODUCTION_RELEASE/DEPLOYED_GIT_SHA')\" = '$EXPECTED_SHA'; cd '$PRODUCTION_RELEASE'; bash deploy/ovh/smoke-candidate.sh '$PRODUCTION_ENV'"

echo "[2/5] Verify every production DNS record"
for domain in "${DOMAINS[@]}"; do
  resolved="$(ssh "$SSH_TARGET" "getent ahostsv4 '$domain' | awk 'NR==1 {print \$1}'")"
  [[ "$resolved" == "$PUBLIC_IPV4" ]] || { echo "DNS NOT READY: $domain -> ${resolved:-missing}" >&2; exit 1; }
  echo "OK   $domain -> $resolved"
done

if ! $APPLY; then
  echo
  echo "DRY RUN passed. No backup or Caddy change was made."
  echo "Rerun with --apply only after final browser acceptance."
  exit 0
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$REMOTE_ROOT/shared/backups/pre-promotion-$timestamp"
remote_candidate="/tmp/keltiawave-Caddyfile.production-$timestamp"

echo "[3/5] Create immutable backups of the legacy production"
ssh "$SSH_TARGET" "set -eu; mkdir -p '$backup_dir'; cp -p '$ACTIVE_CADDY' '$backup_dir/Caddyfile'; docker exec ovh-postgres-1 sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc' > '$backup_dir/legacy-postgres.dump'; docker run --rm -v 'ovh_minio_data:/data:ro' -v '$backup_dir:/backup' alpine:3.20 tar -C /data -czf /backup/legacy-minio.tar.gz .; docker run --rm -v 'ovh_questions_data:/data:ro' -v '$backup_dir:/backup' alpine:3.20 tar -C /data -czf /backup/legacy-app-data.tar.gz .; sha256sum '$backup_dir/'* > '$backup_dir/SHA256SUMS'"

echo "[4/5] Validate and atomically reload Caddy"
scp "$PROJECT_DIR/deploy/ovh/Caddyfile.production" "$SSH_TARGET:$remote_candidate"
ssh "$SSH_TARGET" "set -eu; docker cp '$remote_candidate' ovh-caddy-1:/tmp/Caddyfile.production; docker exec ovh-caddy-1 caddy validate --config /tmp/Caddyfile.production --adapter caddyfile; cp -p '$remote_candidate' '$ACTIVE_CADDY'; if ! docker exec ovh-caddy-1 caddy reload --config /tmp/Caddyfile.production --adapter caddyfile; then docker cp '$backup_dir/Caddyfile' ovh-caddy-1:/tmp/Caddyfile.rollback; docker exec ovh-caddy-1 caddy reload --config /tmp/Caddyfile.rollback --adapter caddyfile; cp -p '$backup_dir/Caddyfile' '$ACTIVE_CADDY'; exit 1; fi"

echo "[5/5] Verify public endpoints; roll back Caddy on failure"
if ! ssh "$SSH_TARGET" "set -eu; domains='${DOMAINS[*]}'; for attempt in \$(seq 1 60); do failed=0; for domain in \$domains; do curl --fail --silent --max-time 15 \"https://\$domain/\" >/dev/null 2>&1 || failed=1; done; if [ \$failed -eq 0 ]; then for domain in \$domains; do echo \"OK   https://\$domain/\"; done; exit 0; fi; echo \"Waiting for HTTPS certificates (attempt \$attempt/60)\"; sleep 5; done; exit 1"; then
  echo "Public verification failed; restoring the previous Caddy configuration" >&2
  ssh "$SSH_TARGET" "set -eu; docker cp '$backup_dir/Caddyfile' ovh-caddy-1:/tmp/Caddyfile.rollback; docker exec ovh-caddy-1 caddy reload --config /tmp/Caddyfile.rollback --adapter caddyfile; cp -p '$backup_dir/Caddyfile' '$ACTIVE_CADDY'"
  exit 1
fi

echo "Production promoted successfully. Legacy containers remain running for rollback."
echo "Backup directory: $backup_dir"
