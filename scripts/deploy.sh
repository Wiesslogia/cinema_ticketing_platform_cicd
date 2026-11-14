#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.yml"
URL="${BASE_URL:-https://cinema.localhost}"

TAG="${1:-}"
[[ "$TAG" =~ ^[0-9a-f]{7}$ ]] || { echo "usage: $0 <7-char-sha>" >&2; exit 1; }

PREV=$(grep '^APP_VERSION=' .env | cut -d= -f2)
sed -i "s/^APP_VERSION=.*/APP_VERSION=$TAG/" .env

if ! $COMPOSE pull app; then
  sed -i "s/^APP_VERSION=.*/APP_VERSION=$PREV/" .env
  echo "pull failed; .env restored to $PREV" >&2; exit 1
fi
$COMPOSE up -d app

code=000
for _ in $(seq 1 30); do
  code=$(curl -ks -m 3 -o /dev/null -w '%{http_code}' "$URL/ready" || true)
  [ "$code" = "200" ] && break
  sleep 2
done
[ "$code" = "200" ] || { echo "NOT READY after deploying $TAG (previous: $PREV)" >&2; exit 1; }

echo "deployed $TAG (previous: $PREV)"
$COMPOSE ps app
docker image inspect --format '{{index .RepoDigests 0}}' "ghcr.io/wiesslogia/cinema-api:$TAG"