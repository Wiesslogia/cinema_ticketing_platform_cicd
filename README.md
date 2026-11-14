# Cinema Show & Seat Reservation API: Cloud Deployment & CI/CD

A small show/seat reservation API (FastAPI + PostgreSQL) built, scanned, released, deployed behind HTTPS, monitored and recoverable with production-style practices. The focus is the delivery pipeline and operations, not application breadth.

- Repository: `<repo URL>` (branch `main`, final commit `<commit id>`)
- Domain rules: temporary seat holds that expire, one confirmed booking per seat (enforced by the database, tested under concurrency), unique ticket IDs, simulated cancellation.

## Architecture
See [docs/architecture.md](docs/architecture.md).

```
Browser --HTTPS 443--> Caddy (proxy) --app:8000--> FastAPI app --db:5432--> PostgreSQL (named volume)
                                  GitHub Actions -> GHCR (SHA-tagged image) -> pulled by the host
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: process is up (does not touch the database) |
| GET | `/ready` | Readiness: database reachable (503 if not) |
| GET | `/version` | Running release (`APP_VERSION`) |
| GET | `/shows` | List shows |
| GET | `/shows/{id}/seats` | Seat map: `AVAILABLE`, `HELD`, `BOOKED` |
| POST | `/shows/{id}/holds` `{"seat":"A1"}` | Hold a seat for `HOLD_TTL_SECONDS` (409 if held or booked) |
| POST | `/bookings` `{"show_id":1,"seat":"A1","hold_token":"..."}` | Confirm a booking, returns `ticket_id` |
| GET | `/bookings/{ticket_id}` | Look up a booking |
| POST | `/bookings/{ticket_id}/cancel` | Cancel (frees the seat) |

Seed data: 2 shows x 24 seats (rows A-C, seats 1-8), loaded from `db/init.sql` on first start.

## Quick start (clean machine)
Requirements: Docker Engine 24+ with the Compose plugin. On RHEL-family systems with SELinux enforcing, the compose file already uses `:z` on bind mounts.

```bash
git clone <repo URL> cinema-api && cd cinema-api
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD (letters and digits only) and APP_VERSION (a 7-char tag, see docs/releases.md)
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml ps          # all three services healthy
curl -k https://cinema.localhost/ready           # {"status":"ready"}
scripts/healthcheck.sh                           # health=200 ready=200
```
`cinema.localhost` resolves to the local machine on most systems; if it does not, add `127.0.0.1 cinema.localhost` to `/etc/hosts`. `-k` is needed because the certificate comes from Caddy's local CA (see Security).

### Two Compose modes
| Command | Loads | Use |
|---|---|---|
| `docker compose -f docker-compose.yml up -d` | base file only | **Deploy mode**: pulls the CI-built image, publishes only 80 and 443 |
| `docker compose up -d` | base + `docker-compose.override.yml` | **Dev mode**: builds the image locally, also publishes `127.0.0.1:8000` and `127.0.0.1:5432` |

### Run the tests (dev mode)
```bash
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
set -a; source .env; set +a
export DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@127.0.0.1:5432/$POSTGRES_DB
pytest -v          # 6 tests, including 20 parallel holds on one seat (exactly one succeeds)
ruff check . && ruff format --check .
```

## Environment variables

| Variable | Purpose | Example | Secret |
|---|---|---|---|
| `POSTGRES_USER` | Database user | `cinema` | no |
| `POSTGRES_PASSWORD` | Database password | set your own | **yes** |
| `POSTGRES_DB` | Database name | `cinema` | no |
| `HOLD_TTL_SECONDS` | Seat hold lifetime (default 300) | `300` | no |
| `APP_VERSION` | Image tag to deploy; also returned by `/version` (required) | `50eddac` | no |
| `DATABASE_URL` | Built by Compose from the values above; set by hand only for local tests | n/a | yes |
| `BASE_URL` | Optional override for the scripts (default `https://cinema.localhost`) | n/a | no |

Only `.env.example` (placeholders) is committed. `.env` is git-ignored.

## Port map

| Port | Deploy mode | Dev mode |
|---|---|---|
| 80 (host) | Proxy: redirects to HTTPS | same |
| 443 (host) | Proxy: HTTPS | same |
| 8000 | App, **internal only** | also `127.0.0.1:8000` |
| 5432 | Postgres, **internal only** | also `127.0.0.1:5432` |

## CI/CD
Workflow: `.github/workflows/ci.yaml`. Triggers: pull requests to `main`, pushes to `main`, and manual runs.

| Job | What it does | Runs |
|---|---|---|
| `lint` | `ruff check` and `ruff format --check` | parallel |
| `test` | Postgres service container, loads `db/init.sql`, `pytest -v` | parallel |
| `build-scan-push` | Builds the image locally, scans it with Trivy, then logs in and pushes | after both pass |

- **Order matters:** the image is built locally and scanned **before** any push, so a vulnerable image never reaches the registry.
- **Push gate:** login and push run only on `push` to `main`. Pull requests build and scan but never publish.
- **Tags:** the 7-character commit SHA (traceable, immutable). `latest` is also pushed for convenience but is never deployed. The digest of each push is written to the job summary.
- **Scan policy:** Trivy fails the job on `HIGH` or `CRITICAL` findings; `ignore-unfixed: true` skips vulnerabilities that have no patch yet.
- **Pipeline safety:** `permissions: contents: read` globally, `packages: write` only on the push job; the built-in `GITHUB_TOKEN` is used (no stored secrets); actions are pinned to major versions.

## Security and network exposure
- Only the proxy publishes ports; the app and database are reachable only on the private Compose network in deploy mode.
- The app image is multi-stage and runs as non-root (uid 10001).
- TLS: Caddy `tls internal` issues a certificate from its own local CA, so browsers warn and `curl` needs `-k`. A public deployment would use a real domain and Let's Encrypt.
- Headers: `Strict-Transport-Security`, `X-Content-Type-Options`; the `Server` header is removed.
- Secrets live in `.env` (git-ignored); the database password never appears in scripts (they read it from the container's own environment).

## Operations (details in [docs/runbook.md](docs/runbook.md))
| Task | Command |
|---|---|
| Health check | `scripts/healthcheck.sh` |
| Logs | `docker compose -f docker-compose.yml logs <app\|db\|proxy> --tail 50` |
| Backup | `scripts/backup.sh` (verified `pg_dump -Fc`, keeps newest 7) |
| Restore | `scripts/restore.sh backups/<file>.dump` |
| Deploy or roll back | `scripts/deploy.sh <7-char-sha>` |

Rollback procedure: [docs/rollback.md](docs/rollback.md). Troubleshooting: [docs/troubleshooting.md](docs/troubleshooting.md).

## Evidence
CI runs, image tag and digest, failure drills, backup/restore and rollback evidence: [docs/evidence.md](docs/evidence.md), [docs/drills.md](docs/drills.md), [docs/backup-restore-evidence.md](docs/backup-restore-evidence.md), [docs/releases.md](docs/releases.md).

## Known limitations and assumptions
- Local deployment only (single host, Docker Compose); no paid cloud hosting.
- The certificate is from a local CA, not a public one.
- Backups are written to the same host as the database; a disk loss would lose both. A production setup would copy them off-host.
- No database migrations; rollback assumes an image rollback never needs a schema change.
- The GHCR package is public so the setup is reproducible without credentials; the image contains no secrets.
- Metrics (stretch goal) are not implemented; observability is health/readiness, structured JSON logs, access logs and a detection script.
- Authentication and payments are out of scope.

## Tech stack
Python 3.12, FastAPI, Uvicorn, psycopg 3 with connection pool, PostgreSQL 16, pytest, ruff, Docker, Docker Compose, Caddy 2, GitHub Actions, GHCR, Trivy.

## Attribution and AI use
- CI workflow adapted from GitHub's "Building and testing Python" and "Publishing Docker images" documentation, and the Trivy action README.
- AI use is declared in [docs/submission-notes.md](docs/submission-notes.md).
