# Submission notes (answers for the form)

Edit anything below that does not match what you actually did. The declarations must be true.

## Assignment
- Internship role: DevOps & Cloud Engineering
- Project: Cloud Deployment & CI/CD – Cinema Ticketing Platform
- Allocated service: Show and seat reservation API

## Code and version
- Repository URL: `<repo URL>` (public, or reviewer access granted to `<reviewer>`)
- Primary branch: `main`
- Final commit ID: `<full sha>`

## Demonstration
- Demo video (3-5 min): `<link, check it opens in a private window>`
- Live demo URL: none, **local-only demo** (Docker Compose on a local VM, HTTPS via a local CA)

## Documentation links
- README: `<repo URL>/blob/main/README.md`
- Architecture diagram: `<repo URL>/blob/main/docs/architecture.md`
- Runbook: `docs/runbook.md`; troubleshooting: `docs/troubleshooting.md`
- Evidence: `docs/evidence.md`, `docs/drills.md`, `docs/backup-restore-evidence.md`, `docs/rollback.md`, `docs/releases.md`

## Role-specific fields
| Field | Value |
|---|---|
| CI/CD pipeline run URL | `<green run URL>` |
| Deployed service URL or local evidence | Local deployment evidence in `docs/evidence.md` |
| Image tag / digest | `50eddac` / `sha256:7f7660396c4ec67d690d1f6106b0c484e28e3a08f8e39e19bf292f40feedf53e` (update if you submit a later release) |
| Architecture diagram | `docs/architecture.md` |
| Backup / restore / rollback evidence | `docs/backup-restore-evidence.md`, `docs/rollback.md` |

## Technology stack and setup notes
Python 3.12, FastAPI, Uvicorn, psycopg 3 (pool), PostgreSQL 16, pytest, ruff, Docker, Docker Compose, Caddy 2 (`tls internal`), GitHub Actions, GHCR, Trivy. Developed on Rocky Linux 10 with Docker CE (SELinux enforcing, so bind mounts use `:z`). Setup: README "Quick start".

## Known incomplete features and assumptions
- Local deployment only; certificate issued by a local CA.
- Backups stored on the same host as the database (no off-host copy).
- No database migrations; rollback is image-only.
- Metrics (stretch goal) not implemented.
- No authentication or payments (out of scope).
- GHCR package is public, and contains no secrets.

## AI and attribution
Tools used: Claude (Anthropic), as a tutor and drafting assistant.

| Area | How AI was involved (edit to match reality) |
|---|---|
| Concepts and decisions | Explanations of Docker/Compose, health vs readiness, locking, CI design, proxy and TLS, backup and rollback; I made the design choices recorded in the README |
| Application, schema, tests, Dockerfile, Compose | Initial reference version drafted with Claude; I ran it, tested it, and can explain each part |
| CI workflow | Written by me from GitHub's documentation and starter workflow; Claude reviewed it and helped diagnose failures (old action version, Trivy findings) |
| Caddyfile, proxy service, dev/deploy split, log rotation | Guided by Claude and typed or adapted by me |
| Scripts (`healthcheck.sh`, `backup.sh`, `restore.sh`, `deploy.sh`) | Drafted with Claude, then executed and verified by me |
| Documentation | README, runbook, troubleshooting and evidence files drafted with Claude, then filled in and corrected with my own outputs |

Sources and libraries: FastAPI, Uvicorn, Starlette, Pydantic, psycopg, PostgreSQL, pytest, ruff, Docker, Caddy, GitHub Actions (`actions/checkout`, `actions/setup-python`, `docker/setup-buildx-action`, `docker/build-push-action`, `docker/login-action`), `aquasecurity/trivy-action`. CI workflow adapted from GitHub's "Building and testing Python" and "Publishing Docker images" docs.

## Declarations
- The work is my own submission and I can explain every part of the code, configuration and scripts, and modify them live.
- No real sensitive data, secrets or credentials are committed (`.env` is git-ignored; only `.env.example` is committed).
- I checked that all links work and that the repository, report and video open without needing my login.
