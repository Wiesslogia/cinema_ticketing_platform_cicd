# Troubleshooting

All commands assume the deploy file is used: `docker compose -f docker-compose.yml ...`
Health script: `scripts/healthcheck.sh` (prints `health=<code> ready=<code>`, exit 1 if `/ready` is not 200).

## Quick triage order
1. `scripts/healthcheck.sh`: what do `health` and `ready` say?
2. `docker compose -f docker-compose.yml ps`: which container is not `healthy`?
3. `docker compose -f docker-compose.yml logs <service> --tail 30`: what is the last error?

## Reading the health script output

| health | ready | Meaning |
|---|---|---|
| 200 | 200 | Healthy |
| 200 | 503 | App is up, database unreachable |
| 502 | 502 | Proxy is up, app is down or unhealthy |
| 000 | 000 | Proxy unreachable (not running, port closed, or wrong URL) |

## Symptoms

| # | Symptom | How to see it | Likely cause | Fix |
|---|---|---|---|---|
| 1 | `/ready` returns 503 | `scripts/healthcheck.sh` shows `ready=503`; app logs contain `"msg": "readiness failed"` | Database stopped, crashed or still starting | `docker compose -f docker-compose.yml ps`; `docker compose -f docker-compose.yml start db`; the app's connection pool reconnects by itself within about 10-20 s, no app restart needed |
| 2 | 502 from the proxy | `curl -ks https://cinema.localhost/ready` returns 502; script shows `502 502`; proxy access log shows `"status":502` | App container is down or restarting, or the Caddyfile points at the wrong service name or port | `docker compose -f docker-compose.yml ps`; if the app is stopped, `docker compose -f docker-compose.yml up -d app`; confirm the Caddyfile says `reverse_proxy app:8000` |
| 3 | `ready=000` (connection refused or timeout) | Script prints `health=000 ready=000`; `curl -kv https://cinema.localhost/health` shows `Connection refused` | Proxy container not running, ports 80/443 not published, or `cinema.localhost` not resolving | `docker compose -f docker-compose.yml ps` (proxy must show `0.0.0.0:443->443`); `docker compose -f docker-compose.yml up -d proxy`; `ping -c1 cinema.localhost` |
| 4 | App container keeps restarting | `docker compose -f docker-compose.yml ps` shows `Restarting`; `docker inspect --format '{{.RestartCount}}' <container>` keeps rising | Wrong `DATABASE_URL`, database not ready, or a code error at startup | `docker compose -f docker-compose.yml logs app --tail 30`; check `.env` values; confirm `db` is `healthy` |
| 5 | `up` fails with `set APP_VERSION in .env` | Compose prints that message and stops | `APP_VERSION` is empty or missing (guard in the compose file) | Set `APP_VERSION=<7-char sha>` in `.env` using a tag that exists in GHCR |
| 6 | Image pull fails with `unauthorized` or `not found` | `docker compose -f docker-compose.yml pull app` prints the error | GHCR package is private, or the tag does not exist (tags are only pushed from `main` runs where the scan passed) | Make the package public, or `docker login ghcr.io` with a read-only token; check the tag under the repo's Packages page |
| 7 | Port 80 or 443 already in use | `up` fails with `address already in use` | Another service on the host (web server, another container) holds the port | `sudo ss -tlnp \| grep -E ':80 \|:443 '`; stop that service or change the proxy's published ports |
| 8 | Browser warns the certificate is not trusted | Browser shows a warning for `cinema.localhost`; `curl` without `-k` fails with a certificate error | Expected: the certificate is issued by Caddy's local CA (`tls internal`), not a public CA | Use `curl -k` for checks, or trust Caddy's root certificate from the `caddy_data` volume. Not an incident in this setup |
| 9 | Tests cannot connect to the database | `pytest` fails with `connection refused` on `127.0.0.1:5432` | Stack was started in deploy mode, which publishes no database port | Start dev mode: `docker compose up -d` (loads `docker-compose.override.yml`); check `DATABASE_URL` matches `.env` |
| 10 | Database container restarts with blank-variable warnings | `up` prints `POSTGRES_USER variable is not set`; `db` shows `Restarting` | `.env` missing, misnamed, or not in `KEY=value` format | `cat .env` (5 lines of `KEY=value`, no commands inside); `docker compose -f docker-compose.yml config -q` |
| 11 | Database starts empty (`relation "shows" does not exist`) or init file unreadable | App logs show the missing-table error; `psql` shows no tables | SELinux (Rocky) blocked the bind mount, or the data volume already existed so `init.sql` did not run | Mount with `:ro,z`. To re-run init on a throwaway environment: `docker compose -f docker-compose.yml down -v` (**destroys all data**, never on a system you need) |
| 12 | CI fails at the Trivy step | Actions log ends with a table showing `HIGH` or `CRITICAL` findings and exit code 1 | A dependency or base-image package has a fixable vulnerability | Upgrade the package pin in `requirements.txt`, or rebuild on a patched base image; document any exception with a reason and a review date |
| 13 | Disk filling up from logs | `docker system df`; large files under `/var/lib/docker/containers/` | Log rotation not applied | Confirm `logging` with `max-size: 10m`, `max-file: 3` on all services: `docker inspect --format '{{.Name}} {{.HostConfig.LogConfig}}' $(docker compose -f docker-compose.yml ps -q)` |

## Behaviour to know during incidents
- `docker kill <app>` (a crash) is restarted automatically by `restart: unless-stopped`; `docker stop <app>` (an operator decision) is not.
- Docker's own `healthy` status for the app comes from `/health`, which does not touch the database. A database outage therefore leaves the app `healthy` in `docker compose ps`; detect it with `scripts/healthcheck.sh` (it watches `/ready`).
