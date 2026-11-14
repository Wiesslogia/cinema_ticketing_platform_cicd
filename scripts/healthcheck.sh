#!/usr/bin/env bash
set -u
URL="${BASE_URL:-https://cinema.localhost}"

# Print only the HTTP status code; curl prints 000 if it cannot connect.
code() { curl -ks -m 3 -o /dev/null -w '%{http_code}' "$URL$1"; }

health=$(code /health)
ready=$(code /ready)

echo "$(date -u +%FT%TZ) health=$health ready=$ready"

[ "$ready" = "200" ] && exit 0
exit 1