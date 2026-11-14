#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.yml"
URL="${BASE_URL:-https://cinema.localhost}"

FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -s "$FILE" ]; then
  echo "usage: $0 backups/<file>.dump" >&2; exit 1
fi

read -r -p "This OVERWRITES the database with $FILE. Type 'yes' to continue: " ans
[ "$ans" = "yes" ] || { echo "aborted"; exit 1; }

# Stop the app so nothing writes during the restore
$COMPOSE stop app

if ! $COMPOSE exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$FILE"; then
  echo "restore FAILED; app left stopped on purpose" >&2; exit 1
fi

$COMPOSE start app

# Wait until the app reports ready
for _ in $(seq 1 30); do
  code=$(curl -ks -m 3 -o /dev/null -w '%{http_code}' "$URL/ready" || true)
  if [ "$code" = "200" ]; then echo "restored; app ready"; exit 0; fi
  sleep 2
done
echo "app did not become ready in 60 s" >&2; exit 1