#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.yml"
KEEP=7

mkdir -p backups
FILE="backups/cinema-$(date -u +%Y%m%dT%H%M%SZ).dump"

# 1. Dump inside the db container (credentials come from its own env vars)
if ! $COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"; then
  rm -f "$FILE"; echo "pg_dump failed" >&2; exit 1
fi

# 2. Verify: file is non-empty and pg_restore can read its table of contents
if [ ! -s "$FILE" ] || ! $COMPOSE exec -T db pg_restore --list < "$FILE" > /dev/null; then
  rm -f "$FILE"; echo "backup verification failed" >&2; exit 1
fi

# 3. Keep only the newest $KEEP backups
ls -1t backups/cinema-*.dump | tail -n +$((KEEP + 1)) | xargs -r rm --

echo "OK $FILE ($(du -h "$FILE" | cut -f1))"