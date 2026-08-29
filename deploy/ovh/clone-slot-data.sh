#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_SLOT="${1:?source slot is required}"
DESTINATION_SLOT="${2:?destination slot is required}"
REMOTE_ROOT="${3:-/home/ubuntu/apps/keltiawave}"
BACKUP_DIR="${4:?backup directory is required}"
COMPOSE_FILE="deploy/ovh/docker-compose.candidate.yml"
SOURCE_RELEASE="$REMOTE_ROOT/releases/$SOURCE_SLOT"
DESTINATION_RELEASE="$REMOTE_ROOT/releases/$DESTINATION_SLOT"
SOURCE_ENV="$REMOTE_ROOT/shared/.env.$SOURCE_SLOT"
DESTINATION_ENV="$REMOTE_ROOT/shared/.env.$DESTINATION_SLOT"
SOURCE_MINIO_VOLUME="keltiawave-${SOURCE_SLOT}_minio_data"
DESTINATION_MINIO_VOLUME="keltiawave-${DESTINATION_SLOT}_minio_data"
ARCHIVE_IMAGE="alpine:3.20"
source_minio_stopped=false

source_compose() {
  docker compose --env-file "$SOURCE_ENV" -f "$SOURCE_RELEASE/$COMPOSE_FILE" "$@"
}

destination_compose() {
  docker compose --env-file "$DESTINATION_ENV" -f "$DESTINATION_RELEASE/$COMPOSE_FILE" "$@"
}

archive_volume() {
  local volume="$1" output_name="$2"
  docker run --rm --entrypoint /bin/sh \
    -v "$volume:/data:ro" \
    -v "$BACKUP_DIR:/backup" \
    "$ARCHIVE_IMAGE" -c "tar -C /data -czf '/backup/$output_name' ."
}

restart_source_minio() {
  if $source_minio_stopped; then
    source_compose start minio >/dev/null
    source_minio_stopped=false
  fi
}
trap restart_source_minio EXIT

test -f "$SOURCE_ENV"
test -f "$SOURCE_RELEASE/$COMPOSE_FILE"
mkdir -p "$BACKUP_DIR"

# Stop destination writers before taking its rollback snapshot.
destination_compose stop backend minio
destination_compose start postgres
destination_compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$BACKUP_DIR/destination-postgres.dump"
archive_volume "$DESTINATION_MINIO_VOLUME" destination-minio.tar.gz

# PostgreSQL provides a transactionally consistent live export.
source_compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$BACKUP_DIR/source-postgres.dump"

# MinIO data files require a short write pause for a consistent filesystem copy.
source_compose stop minio
source_minio_stopped=true
archive_volume "$SOURCE_MINIO_VOLUME" source-minio.tar.gz
restart_source_minio

cat "$BACKUP_DIR/source-postgres.dump" | destination_compose exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner'

docker run --rm --entrypoint /bin/sh \
  -v "$DESTINATION_MINIO_VOLUME:/data" \
  -v "$BACKUP_DIR:/backup:ro" \
  "$ARCHIVE_IMAGE" -c \
  'find /data -mindepth 1 -delete; tar -C /data -xzf /backup/source-minio.tar.gz'

destination_compose up -d
destination_compose up -d --wait backend
